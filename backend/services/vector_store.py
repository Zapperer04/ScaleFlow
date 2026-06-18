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

def get_client():
    global _client
    if _client is not None:
        return _client

    try:
        from qdrant_client import QdrantClient
        from qdrant_client.http import models as qmodels  # noqa: F401
    except Exception:
        # qdrant_client is not available; raise a clear ImportError when actually
        # attempting to use the client.
        raise

    if os.environ.get("DB_MODE") == "sqlite":
        logger.info("SQLite mode detected: Using in-memory QdrantClient fallback")
        _client = QdrantClient(location=":memory:")
    else:
        try:
            _client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=12.0)
            _client.get_collections()
        except Exception as e:
            logger.warning(f"Could not connect to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}: {e}. Falling back to in-memory QdrantClient.")
            _client = QdrantClient(location=":memory:")

    return _client

COLLECTIONS = {
    "chunks": config.QDRANT_COLLECTION_NAME,
    "paragraphs": config.QDRANT_PARAGRAPH_COLLECTION,
    "tables": config.QDRANT_TABLE_COLLECTION,
}

def ensure_collections_exist():
    try:
        client = get_client()
        from qdrant_client.http import models as qmodels
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

            # Always ensure payload indexes exist (idempotent)
            _index_specs = [
                ("pipeline_id", qmodels.PayloadSchemaType.INTEGER),
                ("file_id", qmodels.PayloadSchemaType.INTEGER),
                ("section", qmodels.PayloadSchemaType.KEYWORD),
                ("content_type", qmodels.PayloadSchemaType.KEYWORD),
            ]
            for field_name, field_schema in _index_specs:
                try:
                    client.create_payload_index(
                        collection_name=name,
                        field_name=field_name,
                        field_schema=field_schema,
                    )
                    logger.info(f"Created payload index '{field_name}' on '{name}'")
                except Exception:
                    pass  # index already exists
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
        from qdrant_client.http import models as qmodels

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
            # Create payload indexes on the newly created collection
            _index_specs = [
                ("pipeline_id", qmodels.PayloadSchemaType.INTEGER),
                ("file_id", qmodels.PayloadSchemaType.INTEGER),
                ("section", qmodels.PayloadSchemaType.KEYWORD),
                ("content_type", qmodels.PayloadSchemaType.KEYWORD),
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
                    pass
        _ensured_collections.add(collection_name)
        return True
    except Exception as e:
        logger.error(f"Failed to ensure Qdrant collection {collection_name}: {e}")
        return False

def upsert_document_chunks(pipeline_id, file_id, task_id, chunks, vectors, metadata=None, collection_name=None):
    if collection_name is None:
        collection_name = config.QDRANT_COLLECTION_NAME
        
    print("=" * 80, flush=True)
    print("QDRANT INSERTION COLLECTION NAME:", collection_name, flush=True)
    print("=" * 80, flush=True)

    import time
    t_lookup_start = time.perf_counter()
    # Ensure client is available and collection exists
    try:
        client = get_client()
        from qdrant_client.http import models as qmodels
    except Exception as e:
        logger.error(f"Qdrant client not available: {e}")
        return False, 0.0, 0.0

    has_collection = ensure_collection(collection_name, config.EMBEDDING_DIMENSION)
    lookup_duration = time.perf_counter() - t_lookup_start

    if not has_collection:
        logger.error("Could not ensure collection exists in Qdrant. Aborting upsert.")
        return False, lookup_duration, 0.0
        
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
    for i, (chunk_text, vector) in enumerate(zip(chunks, vectors)):
        point_id = str(uuid.uuid4())
        
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
            "chunk_index": i,
            "chunk_text": chunk_text,
            "source_artifact_id": global_meta.get("source_artifact_id") if global_meta else None,
            "original_filename": global_meta.get("original_filename") if global_meta else None,
            "created_at": datetime.utcnow().isoformat(),
            
            # Compatibility keys for step 3
            "document_id": stored_file_id,
            "filename": global_meta.get("original_filename") if global_meta else None,
            "chunk_id": i,
            "text": chunk_text,
            
            # Default metadata fields
            "section": "unknown",
            "content_type": "paragraph",
            "token_count": 0,
            "page_number": 0
        }
        
        # Merge chunk-specific metadata fields
        if chunk_meta_list and i < len(chunk_meta_list):
            c_meta = chunk_meta_list[i]
            if isinstance(c_meta, dict):
                if "metadata" in c_meta and isinstance(c_meta["metadata"], dict):
                    c_meta = c_meta["metadata"]
                payload.update(c_meta)
        
        # Add collection_source to chunk metadata in Qdrant payload
        if collection_name == config.QDRANT_TABLE_COLLECTION:
            payload["collection_source"] = "tables"
        elif collection_name == config.QDRANT_PARAGRAPH_COLLECTION:
            payload["collection_source"] = "paragraphs"
        else:
            payload["collection_source"] = "tables" if payload.get("content_type") == "table" else "paragraphs"
        
        points.append(
            qmodels.PointStruct(
                id=point_id,
                vector=vector,
                payload=payload
            )
        )
        
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

    t_insert_start = time.perf_counter()
    try:
        client.upsert(
            collection_name=collection_name,
            points=points
        )
        insertion_duration = time.perf_counter() - t_insert_start
        logger.info(f"Successfully upserted {len(points)} chunks to collection {collection_name} (took {insertion_duration:.4f}s)")
        return True, lookup_duration, insertion_duration
    except Exception as e:
        logger.error(f"Failed to upsert chunks to Qdrant: {e}")
        insertion_duration = time.perf_counter() - t_insert_start
        return False, lookup_duration, insertion_duration

def search_similar(collection_name, query_vector, top_k=5, filters=None):
    print("=" * 80, flush=True)
    print("QDRANT RETRIEVAL COLLECTION NAME:", collection_name, flush=True)
    print("=" * 80, flush=True)
    try:
        ensure_collection(collection_name, config.EMBEDDING_DIMENSION)
        client = get_client()
        from qdrant_client.http import models as qmodels
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
            results.append({
                "score": round(hit.score, 4),
                "chunk_text": hit.payload.get("chunk_text"),
                "text": hit.payload.get("text") or hit.payload.get("chunk_text"),
                "section": hit.payload.get("section", "unknown"),
                "pipeline_id": hit.payload.get("pipeline_id"),
                "file_id": hit.payload.get("file_id"),
                "task_id": hit.payload.get("task_id"),
                "chunk_index": hit.payload.get("chunk_index"),
                "original_filename": hit.payload.get("original_filename"),
                "page_number": hit.payload.get("page_number"),
                "document_type": hit.payload.get("document_type"),
                "routing_confidence": hit.payload.get("routing_confidence"),
                "ocr_engine": hit.payload.get("ocr_engine"),
                "ocr_confidence": hit.payload.get("ocr_confidence"),
                "extraction_method": hit.payload.get("extraction_method"),
                "table_detected": hit.payload.get("table_detected"),
                "contains_signature": hit.payload.get("contains_signature"),
                "contains_handwriting": hit.payload.get("contains_handwriting"),
                "chunk_quality_score": hit.payload.get("chunk_quality_score")
            })
        return results
    except Exception as e:
        logger.error(f"Failed to search similar in Qdrant: {e}")
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

