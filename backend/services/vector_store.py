import os
import uuid
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", 6333))

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Lazily-initialized Qdrant client so importing this module doesn't require the
# `qdrant_client` package to be installed (useful for unit/integration tests
# that mock the upsert/search functions).
_client = None
qmodels = None

def _make_qdrant_client():
    """Create a fresh QdrantClient. Falls back to in-memory on failure."""
    # Save original sys.path and remove parent directory to prevent models.py shadowing
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    original_sys_path = sys.path[:]
    sys.path = [p for p in sys.path if os.path.abspath(p) != os.path.abspath(parent_dir)]

    try:
        from qdrant_client import QdrantClient
        from qdrant_client.http import models as qm
        global qmodels
        qmodels = qm
    except Exception:
        sys.path = original_sys_path
        raise
    finally:
        sys.path = original_sys_path

    if os.environ.get("DB_MODE") == "sqlite":
        logger.info("SQLite mode detected: Using in-memory QdrantClient fallback")
        return QdrantClient(location=":memory:")
    else:
        try:
            client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=12.0)
            client.get_collections()  # liveness probe
            return client
        except Exception as e:
            logger.warning(f"Could not connect to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}: {e}. Falling back to in-memory QdrantClient.")
            return QdrantClient(location=":memory:")

def get_client():
    global _client
    if _client is not None:
        # Liveness probe: reset stale client after Qdrant restart
        try:
            _client.get_collections()
            return _client
        except Exception as e:
            logger.warning(f"Qdrant liveness probe failed ({e}). Reconnecting...")
            _client = None

    _client = _make_qdrant_client()
    return _client


COLLECTIONS = {
    "chunks": config.QDRANT_COLLECTION_NAME,
    "paragraphs": config.QDRANT_PARAGRAPH_COLLECTION,
    "tables": config.QDRANT_TABLE_COLLECTION,
}

def _create_payload_indexes(client, collection_name):
    """Helper to create all payload indexes on a collection."""
    _index_specs = [
        ("pipeline_id", qmodels.PayloadSchemaType.INTEGER),
        ("file_id", qmodels.PayloadSchemaType.INTEGER),
        ("section", qmodels.PayloadSchemaType.KEYWORD),
        ("content_type", qmodels.PayloadSchemaType.KEYWORD),
        ("chunk_id", qmodels.PayloadSchemaType.KEYWORD),
        ("section_path", qmodels.PayloadSchemaType.KEYWORD),
        ("graph_depth", qmodels.PayloadSchemaType.FLOAT),
        ("importance_score", qmodels.PayloadSchemaType.FLOAT),
        ("entities", qmodels.PayloadSchemaType.KEYWORD),
        ("keywords", qmodels.PayloadSchemaType.KEYWORD),
        ("semantic_parent", qmodels.PayloadSchemaType.KEYWORD),
        ("semantic_children", qmodels.PayloadSchemaType.KEYWORD),
        ("neighbors", qmodels.PayloadSchemaType.KEYWORD),
        ("collection_source", qmodels.PayloadSchemaType.KEYWORD),
        ("page_start", qmodels.PayloadSchemaType.INTEGER),
        ("page_end", qmodels.PayloadSchemaType.INTEGER),
        ("parser_version", qmodels.PayloadSchemaType.KEYWORD),
    ]
    for field_name, field_schema in _index_specs:
        try:
            client.create_payload_index(
                collection_name=collection_name,
                field_name=field_name,
                field_schema=field_schema,
            )
            logger.info(f"Created payload index '{field_name}' on '{collection_name}'")
        except Exception:
            pass  # index already exists

    # Ensure text index for chunk_text
    try:
        client.create_payload_index(
            collection_name=collection_name,
            field_name="chunk_text",
            field_schema=qmodels.TextIndexParams(
                type=qmodels.TextIndexType.TEXT,
                tokenizer=qmodels.TokenizerType.WORD,
                lowercase=True,
            )
        )
        logger.info(f"Created text payload index on '{collection_name}'")
    except Exception:
        try:
            client.create_payload_index(
                collection_name=collection_name,
                field_name="chunk_text",
                field_schema="text"
            )
        except Exception:
            pass

def ensure_collections_exist():
    try:
        client = get_client()
        existing = [c.name for c in client.get_collections().collections]
        for name in COLLECTIONS.values():
            if name not in existing:
                logger.info(f"Creating Qdrant collection: {name}")
                client.create_collection(
                    collection_name=name,
                    vectors_config=qmodels.VectorParams(
                        size=config.EMBEDDING_DIMENSION,
                        distance=qmodels.Distance.COSINE
                    )
                )
            _create_payload_indexes(client, name)
    except Exception as e:
        logger.error(f"Failed to ensure collections exist: {e}")

_ensured_collections = set()

def ensure_collection(collection_name="scaleflow_chunks", vector_size=None):
    global _ensured_collections
    if collection_name in _ensured_collections:
        return True
        
    if vector_size is None:
        vector_size = config.EMBEDDING_DIMENSION
    try:
        client = get_client()

        collections = client.get_collections().collections
        exists = any(c.name == collection_name for c in collections)
        if not exists:
            logger.info(f"Creating Qdrant collection: {collection_name} (size: {vector_size})")
            client.create_collection(
                collection_name=collection_name,
                vectors_config=qmodels.VectorParams(
                    size=vector_size,
                    distance=qmodels.Distance.COSINE
                )
            )
        _create_payload_indexes(client, collection_name)
        _ensured_collections.add(collection_name)
        return True
    except Exception as e:
        logger.error(f"Failed to ensure Qdrant collection {collection_name}: {e}")
        return False

def upsert_document_chunks(pipeline_id, file_id, task_id, chunks, vectors, metadata=None, collection_name=None, chunk_indices=None):
    if collection_name is None:
        collection_name = config.QDRANT_COLLECTION_NAME
        
    # Development logging – gate behind config.DEBUG_VECTOR_STORE if desired
    if getattr(config, 'DEBUG_VECTOR_STORE', False):
        print("=" * 80, flush=True)
        print("QDRANT INSERTION COLLECTION NAME:", collection_name, flush=True)
        print("=" * 80, flush=True)

    import time
    t_lookup_start = time.perf_counter()
    # Ensure client is available and collection exists
    try:
        client = get_client()
    except Exception as e:
        logger.error(f"Qdrant client not available: {e}")
        return False, 0.0, 0.0

    has_collection = ensure_collection(collection_name, config.EMBEDDING_DIMENSION)
    lookup_duration = time.perf_counter() - t_lookup_start

    if not has_collection:
        logger.error("Could not ensure collection exists in Qdrant. Aborting upsert.")
        return False, lookup_duration, 0.0

    # Remove delete-before-upsert – upsert with deterministic IDs will overwrite old entries

    global_meta = {}
    chunk_meta_list = None

    if isinstance(metadata, dict):
        if "chunk_metadata" in metadata and "global_metadata" in metadata:
            global_meta = metadata["global_metadata"] or {}
            chunk_meta_list = metadata["chunk_metadata"]
        else:
            global_meta = metadata
    elif isinstance(metadata, list):
        chunk_meta_list = metadata

    points = []
    for i, (chunk_data, vector) in enumerate(zip(chunks, vectors)):
        # Check if vector is all zero (with epsilon)
        if isinstance(vector, (list, tuple)) and len(vector) > 0:
            if all(abs(v) < 1e-12 for v in vector):
                logger.warning(f"Skipping chunk index {i} because vector is essentially zero (embed=False or empty text).")
                continue

        # Determine if chunk should be skipped based on embed flag
        if isinstance(chunk_data, dict) and chunk_data.get("embed") is False:
            logger.warning(f"Skipping chunk index {i} because embed=False flag is set.")
            continue

        pt_index = chunk_indices[i] if chunk_indices is not None else i

        # Extract metadata from chunk_data, normalising via 'metadata' key
        if isinstance(chunk_data, dict):
            meta = chunk_data.get("metadata", chunk_data)
        else:
            meta = {}

        # Determine chunk_id: use graph-native chunk_id if available, else fallback to deterministic UUID
        chunk_id = chunk_data.get("chunk_id") if isinstance(chunk_data, dict) else None
        if not chunk_id:
            chunk_id = meta.get("chunk_id")
        if not chunk_id:
            # Fallback: deterministic UUID from pipeline_id, file_id, and index
            chunk_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{pipeline_id}_{file_id}_{pt_index}"))

        # Use chunk_id as the Qdrant point ID (deterministic, stable)
        point_id = chunk_id

        # Extract fields from meta (with fallback to chunk_data)
        if isinstance(chunk_data, dict):
            chunk_text = chunk_data.get("text", "")
            bm25_text = chunk_data.get("bm25_text", chunk_text)
            # Remove duplicated fields: we keep chunk_text and bm25_text only if different,
            # but we can store both; we'll drop 'text' and 'embedding_text' to reduce bloat.
            # We'll store chunk_text as the main text and bm25_text separately.
            # If bm25_text is identical to chunk_text, we can omit it (store only chunk_text)
            if bm25_text == chunk_text:
                bm25_text = None  # will not store
            section = meta.get("section") or chunk_data.get("section", "unknown")
            content_type = meta.get("content_type") or chunk_data.get("content_type", "paragraph")
            section_path = meta.get("section_path") or chunk_data.get("section_path", "")
            # Normalize list-based fields
            raw_neighbors = chunk_data.get("neighbors", [])
            neighbors = [str(x) for x in raw_neighbors if x is not None]
            raw_semantic_children = chunk_data.get("semantic_children", [])
            semantic_children = [str(x) for x in raw_semantic_children if x is not None]
            raw_entities = chunk_data.get("entities", [])
            entities = []
            for e in raw_entities:
                if isinstance(e, dict):
                    entities.append(str(e.get("value", e)))
                else:
                    entities.append(str(e))
            raw_keywords = chunk_data.get("keywords", [])
            keywords = [str(k) for k in raw_keywords if k is not None]
            node_ids = chunk_data.get("node_ids", [])
            cross_refs = chunk_data.get("cross_refs", {})
            semantic_parent = chunk_data.get("semantic_parent")
            graph_depth = chunk_data.get("graph_depth", 0)
            importance_score = chunk_data.get("importance_score", 0.0)
            bbox = chunk_data.get("bbox", {})
            pages = chunk_data.get("pages", [])
            token_count = chunk_data.get("token_count", 0)
            char_count = chunk_data.get("char_count", 0)
            page_start = meta.get("page_start") or chunk_data.get("page_start")
            page_end = meta.get("page_end") or chunk_data.get("page_end")
            parser_version = meta.get("parser_version") or chunk_data.get("parser_version")
        else:
            # Legacy string
            chunk_text = str(chunk_data) if chunk_data else ""
            bm25_text = None
            section = "unknown"
            content_type = "paragraph"
            section_path = ""
            node_ids = []
            neighbors = []
            cross_refs = {}
            semantic_parent = None
            semantic_children = []
            entities = []
            keywords = []
            graph_depth = 0
            importance_score = 0.0
            bbox = {}
            pages = []
            token_count = 0
            char_count = 0
            page_start = None
            page_end = None
            parser_version = None

        # Build payload
        stored_pipeline_id = pipeline_id
        if pipeline_id is not None:
            try:
                stored_pipeline_id = int(pipeline_id)
            except (ValueError, TypeError):
                pass
                
        stored_file_id = file_id
        if file_id is not None:
            try:
                stored_file_id = int(file_id)
            except (ValueError, TypeError):
                pass

        payload = {
            "pipeline_id": stored_pipeline_id,
            "file_id": stored_file_id,
            "task_id": task_id,
            "chunk_index": pt_index,
            "chunk_text": chunk_text,
            "source_artifact_id": global_meta.get("source_artifact_id") if global_meta else None,
            "original_filename": global_meta.get("original_filename") if global_meta else None,
            "created_at": datetime.utcnow().isoformat(),
            
            # Compatibility keys (remove 'text' and 'embedding_text' to reduce duplication)
            "document_id": stored_file_id,
            "filename": global_meta.get("original_filename") if global_meta else None,
            "chunk_id": chunk_id,
            
            # Graph-native fields
            "bm25_text": bm25_text,  # may be None if identical to chunk_text
            "node_ids": node_ids,
            "neighbors": neighbors,
            "cross_refs": cross_refs,
            "semantic_parent": semantic_parent,
            "semantic_children": semantic_children,
            "entities": entities,
            "keywords": keywords,
            "section": section,
            "content_type": content_type,
            "section_path": section_path,
            "graph_depth": graph_depth,
            "importance_score": importance_score,
            "bbox": bbox,
            "pages": pages,
            "token_count": token_count,
            "char_count": char_count,
            "page_start": page_start,
            "page_end": page_end,
            "parser_version": parser_version,
        }
        # Remove None values to save space
        payload = {k: v for k, v in payload.items() if v is not None}
        
        # Merge chunk-specific metadata from external metadata list (if any)
        if chunk_meta_list and i < len(chunk_meta_list):
            c_meta = chunk_meta_list[i]
            if isinstance(c_meta, dict):
                if "metadata" in c_meta and isinstance(c_meta["metadata"], dict):
                    c_meta = c_meta["metadata"]
                # Merge only missing keys or override if explicitly provided
                for k, v in c_meta.items():
                    if k not in payload or payload.get(k) is None:
                        payload[k] = v
        
        # Add collection_source
        if collection_name == config.QDRANT_TABLE_COLLECTION:
            payload["collection_source"] = "tables"
        elif collection_name == config.QDRANT_PARAGRAPH_COLLECTION:
            payload["collection_source"] = "paragraphs"
        else:
            payload["collection_source"] = "tables" if content_type == "table" else "paragraphs"
        
        points.append(
            qmodels.PointStruct(
                id=point_id,
                vector=vector,
                payload=payload
            )
        )
        
    if getattr(config, 'DEBUG_VECTOR_STORE', False):
        print("=" * 80, flush=True)
        print("INSERTING VECTOR PAYLOADS TO QDRANT (EXAMPLES):", flush=True)
        for idx, pt in enumerate(points[:5]):
            safe_payload = {}
            for k, v in pt.payload.items():
                if isinstance(v, str):
                    safe_payload[k] = v.encode(sys.stdout.encoding or 'utf-8', errors='ignore').decode(sys.stdout.encoding or 'utf-8')
                else:
                    safe_payload[k] = v
            print(f"Point {idx}: {safe_payload}", flush=True)
        if len(points) > 5:
            print(f"... and {len(points) - 5} more points.", flush=True)
        print("=" * 80, flush=True)

    if not points:
        logger.warning("No points to upsert (all skipped due to zero vectors or embed=False).")
        return True, lookup_duration, 0.0

    t_insert_start = time.perf_counter()
    try:
        # Use configurable batch size
        batch_size = getattr(config, 'UPSERT_BATCH_SIZE', 256)
        for offset in range(0, len(points), batch_size):
            batch_points = points[offset:offset + batch_size]
            client.upsert(
                collection_name=collection_name,
                points=batch_points
            )
        insertion_duration = time.perf_counter() - t_insert_start
        logger.info(f"Successfully upserted {len(points)} chunks to collection {collection_name} (took {insertion_duration:.4f}s)")
        return True, lookup_duration, insertion_duration
    except Exception as e:
        logger.error(f"Failed to upsert chunks to Qdrant: {e}")
        insertion_duration = time.perf_counter() - t_insert_start
        return False, lookup_duration, insertion_duration

def search_similar(collection_name, query_vector, top_k=5, filters=None):
    if getattr(config, 'DEBUG_VECTOR_STORE', False):
        print("=" * 80, flush=True)
        print("QDRANT RETRIEVAL COLLECTION NAME:", collection_name, flush=True)
        print("=" * 80, flush=True)
    try:
        ensure_collection(collection_name, config.EMBEDDING_DIMENSION)
        client = get_client()
        # Build filter if present
        q_filter = None
        if filters:
            conditions = []
            for key, val in filters.items():
                if val is not None:
                    val_to_match = val
                    if key in ("pipeline_id", "file_id"):
                        try:
                            val_to_match = int(val)
                        except (ValueError, TypeError):
                            pass
                    conditions.append(
                        qmodels.FieldCondition(
                            key=key,
                            match=qmodels.MatchValue(value=val_to_match)
                        )
                    )
            if conditions:
                q_filter = qmodels.Filter(must=conditions)
                
        search_result = client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=top_k,
            query_filter=q_filter
        )
        
        results = []
        for hit in search_result:
            payload = hit.payload
            results.append({
                "score": round(hit.score, 4),
                "text": payload.get("chunk_text"),  # backward compatibility
                "chunk_text": payload.get("chunk_text"),
                "section": payload.get("section", "unknown"),
                "pipeline_id": payload.get("pipeline_id"),
                "file_id": payload.get("file_id"),
                "task_id": payload.get("task_id"),
                "chunk_index": payload.get("chunk_index"),
                "original_filename": payload.get("original_filename"),
                "page_number": payload.get("page_number"),
                "document_type": payload.get("document_type"),
                "routing_confidence": payload.get("routing_confidence"),
                "ocr_engine": payload.get("ocr_engine"),
                "ocr_confidence": payload.get("ocr_confidence"),
                "extraction_method": payload.get("extraction_method"),
                "table_detected": payload.get("table_detected"),
                "contains_signature": payload.get("contains_signature"),
                "contains_handwriting": payload.get("contains_handwriting"),
                "chunk_quality_score": payload.get("chunk_quality_score"),
                # Graph-native fields
                "chunk_id": payload.get("chunk_id"),
                "bm25_text": payload.get("bm25_text"),
                "node_ids": payload.get("node_ids", []),
                "neighbors": payload.get("neighbors", []),
                "cross_refs": payload.get("cross_refs", {}),
                "semantic_parent": payload.get("semantic_parent"),
                "semantic_children": payload.get("semantic_children", []),
                "entities": payload.get("entities", []),
                "keywords": payload.get("keywords", []),
                "section_path": payload.get("section_path", ""),
                "graph_depth": payload.get("graph_depth", 0),
                "importance_score": payload.get("importance_score", 0.0),
                "bbox": payload.get("bbox", {}),
                "pages": payload.get("pages", []),
                "token_count": payload.get("token_count", 0),
                "char_count": payload.get("char_count", 0),
                "page_start": payload.get("page_start"),
                "page_end": payload.get("page_end"),
                "parser_version": payload.get("parser_version"),
                # Retrieval metadata
                "retrieval_type": "dense",
                "retrieval_backend": "qdrant",
                "retrieval_score": round(hit.score, 4),
            })
        return results
    except Exception as e:
        logger.error(f"Failed to search similar in Qdrant: {e}")
        return []

def search_keyword(collection_name, query_text, top_k=5, filters=None):
    try:
        ensure_collection(collection_name, config.EMBEDDING_DIMENSION)
        client = get_client()
        
        conditions = []
        if filters:
            for key, val in filters.items():
                if val is not None:
                    val_to_match = val
                    if key in ("pipeline_id", "file_id"):
                        try:
                            val_to_match = int(val)
                        except (ValueError, TypeError):
                            pass
                    conditions.append(
                        qmodels.FieldCondition(
                            key=key,
                            match=qmodels.MatchValue(value=val_to_match)
                        )
                    )
                    
        conditions.append(
            qmodels.FieldCondition(
                key="chunk_text",
                match=qmodels.MatchText(text=query_text)
            )
        )
        
        scroll_filter = qmodels.Filter(must=conditions)
        
        scroll_result, _ = client.scroll(
            collection_name=collection_name,
            scroll_filter=scroll_filter,
            limit=top_k,
            with_payload=True,
            with_vectors=False
        )
        
        results = []
        for point in scroll_result:
            payload = point.payload
            results.append({
                "score": 1.0,  # nominal score before reranking
                "text": payload.get("chunk_text"),  # backward compatibility
                "chunk_text": payload.get("chunk_text"),
                "section": payload.get("section", "unknown"),
                "pipeline_id": payload.get("pipeline_id"),
                "file_id": payload.get("file_id"),
                "task_id": payload.get("task_id"),
                "chunk_index": payload.get("chunk_index"),
                "original_filename": payload.get("original_filename"),
                "page_number": payload.get("page_number"),
                "document_type": payload.get("document_type"),
                "routing_confidence": payload.get("routing_confidence"),
                "ocr_engine": payload.get("ocr_engine"),
                "ocr_confidence": payload.get("ocr_confidence"),
                "extraction_method": payload.get("extraction_method"),
                "table_detected": payload.get("table_detected"),
                "contains_signature": payload.get("contains_signature"),
                "contains_handwriting": payload.get("contains_handwriting"),
                "chunk_quality_score": payload.get("chunk_quality_score"),
                # Graph-native fields
                "chunk_id": payload.get("chunk_id"),
                "bm25_text": payload.get("bm25_text"),
                "node_ids": payload.get("node_ids", []),
                "neighbors": payload.get("neighbors", []),
                "cross_refs": payload.get("cross_refs", {}),
                "semantic_parent": payload.get("semantic_parent"),
                "semantic_children": payload.get("semantic_children", []),
                "entities": payload.get("entities", []),
                "keywords": payload.get("keywords", []),
                "section_path": payload.get("section_path", ""),
                "graph_depth": payload.get("graph_depth", 0),
                "importance_score": payload.get("importance_score", 0.0),
                "bbox": payload.get("bbox", {}),
                "pages": payload.get("pages", []),
                "token_count": payload.get("token_count", 0),
                "char_count": payload.get("char_count", 0),
                "page_start": payload.get("page_start"),
                "page_end": payload.get("page_end"),
                "parser_version": payload.get("parser_version"),
                # Retrieval metadata
                "retrieval_type": "keyword",
                "retrieval_backend": "qdrant_text",
                "retrieval_score": 1.0,
            })
        return results
    except Exception as e:
        logger.error(f"Failed to search keyword in Qdrant: {e}")
        return []

def get_collection_stats(collection_name="scaleflow_chunks"):
    try:
        # Ensure collection configured
        ensure_collection(collection_name, config.EMBEDDING_DIMENSION)
        client = get_client()
        info = client.get_collection(collection_name=collection_name)
        return {
            "collection": collection_name,
            "points_count": info.points_count,
            "vector_size": config.EMBEDDING_DIMENSION,
            "status": "ok"
        }
    except Exception as e:
        logger.error(f"Failed to get collection stats: {e}")
        return {
            "collection": collection_name,
            "points_count": 0,
            "vector_size": config.EMBEDDING_DIMENSION,
            "status": "error",
            "error": str(e)
        }

# For backward compatibility with import references to `from services.vector_store import client`
class _ClientProxy:
    def __getattr__(self, name):
        return getattr(get_client(), name)
client = _ClientProxy()