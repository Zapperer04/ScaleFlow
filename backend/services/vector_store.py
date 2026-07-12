import os
import uuid
import logging
import time
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------
QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", 6333))
QDRANT_TIMEOUT = float(os.environ.get("QDRANT_TIMEOUT", 60.0))
EMBEDDING_MODEL_NAME = os.environ.get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
EMBEDDING_VERSION = "1.0"
SCHEMA_VERSION = "2.0"

UPSERT_MAX_RETRIES = int(os.environ.get("UPSERT_MAX_RETRIES", 3))
UPSERT_RETRY_DELAY_BASE = float(os.environ.get("UPSERT_RETRY_DELAY_BASE", 1.0))
UPSERT_RETRY_DELAY_MAX = float(os.environ.get("UPSERT_RETRY_DELAY_MAX", 30.0))

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Lazily-initialized Qdrant client
_client = None
qmodels = None

def _make_qdrant_client():
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
        logger.info("SQLite mode: Using in-memory QdrantClient fallback")
        return QdrantClient(location=":memory:")
    else:
        try:
            client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=QDRANT_TIMEOUT)
            client.get_collections()
            return client
        except Exception as e:
            logger.warning(f"Could not connect to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}: {e}. Falling back to in-memory.")
            return QdrantClient(location=":memory:")

def get_client():
    global _client
    if _client is not None:
        try:
            _client.get_collections()
            return _client
        except Exception as e:
            logger.warning(f"Qdrant liveness probe failed ({e}). Reconnecting...")
            _client = None
    _client = _make_qdrant_client()
    return _client

def reset_client():
    global _client
    _client = None

COLLECTIONS = {
    "chunks": config.QDRANT_COLLECTION_NAME,
    "paragraphs": config.QDRANT_PARAGRAPH_COLLECTION,
    "tables": config.QDRANT_TABLE_COLLECTION,
}

def _create_payload_indexes(client, collection_name):
    """Create all payload indexes on a collection."""
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
        ("document_id", qmodels.PayloadSchemaType.INTEGER),
        ("filename", qmodels.PayloadSchemaType.KEYWORD),
        ("semantic_category", qmodels.PayloadSchemaType.KEYWORD),
        ("heading_path", qmodels.PayloadSchemaType.KEYWORD),
        ("schema_version", qmodels.PayloadSchemaType.KEYWORD),
        ("embedding_model", qmodels.PayloadSchemaType.KEYWORD),
        ("embedding_version", qmodels.PayloadSchemaType.KEYWORD),
        ("embedding_hash", qmodels.PayloadSchemaType.KEYWORD),
    ]
    for field_name, field_schema in _index_specs:
        try:
            client.create_payload_index(
                collection_name=collection_name,
                field_name=field_name,
                field_schema=field_schema,
            )
        except Exception as e:
            logger.debug(f"Index '{field_name}' on '{collection_name}' already exists or creation failed: {e}")

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
    except Exception as e:
        logger.debug(f"Text index on '{collection_name}' already exists or creation failed: {e}")

def _collection_exists(client, collection_name: str) -> bool:
    try:
        collections = client.get_collections().collections
        return any(c.name == collection_name for c in collections)
    except Exception:
        return False

def _get_collection_info(client, collection_name: str) -> Optional[dict]:
    try:
        return client.get_collection(collection_name=collection_name)
    except Exception:
        return None

def ensure_collections_exist():
    try:
        client = get_client()
        existing_names = {c.name for c in client.get_collections().collections}
        for name in COLLECTIONS.values():
            if name not in existing_names:
                logger.info(f"Creating Qdrant collection: {name}")
                client.create_collection(
                    collection_name=name,
                    vectors_config=qmodels.VectorParams(
                        size=config.EMBEDDING_DIMENSION,
                        distance=qmodels.Distance.COSINE
                    )
                )
            else:
                info = _get_collection_info(client, name)
                if info and info.vectors_config.params.size != config.EMBEDDING_DIMENSION:
                    logger.error(
                        f"Collection '{name}' has dimension {info.vectors_config.params.size}, "
                        f"but config expects {config.EMBEDDING_DIMENSION}. "
                        f"Please recreate the collection or adjust config."
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
        exists = _collection_exists(client, collection_name)
        if not exists:
            logger.info(f"Creating Qdrant collection: {collection_name} (size: {vector_size})")
            client.create_collection(
                collection_name=collection_name,
                vectors_config=qmodels.VectorParams(
                    size=vector_size,
                    distance=qmodels.Distance.COSINE
                )
            )
        else:
            info = _get_collection_info(client, collection_name)
            if info and info.vectors_config.params.size != vector_size:
                logger.error(
                    f"Collection '{collection_name}' has dimension {info.vectors_config.params.size}, "
                    f"but expected {vector_size}. Please recreate the collection."
                )
        _create_payload_indexes(client, collection_name)
        _ensured_collections.add(collection_name)
        return True
    except Exception as e:
        logger.error(f"Failed to ensure Qdrant collection {collection_name}: {e}")
        return False

def upsert_document_chunks(
    pipeline_id,
    file_id,
    task_id,
    chunks,
    vectors,
    metadata=None,
    collection_name=None,
    chunk_indices=None
) -> Tuple[bool, float, float, int]:
    if collection_name is None:
        collection_name = config.QDRANT_COLLECTION_NAME

    if getattr(config, 'DEBUG_VECTOR_STORE', False):
        print("=" * 80, flush=True)
        print("QDRANT INSERTION COLLECTION NAME:", collection_name, flush=True)
        print("=" * 80, flush=True)

    t_lookup_start = time.perf_counter()
    try:
        client = get_client()
    except Exception as e:
        logger.error(f"Qdrant client not available: {e}")
        return False, 0.0, 0.0, 0

    has_collection = ensure_collection(collection_name, config.EMBEDDING_DIMENSION)
    lookup_duration = time.perf_counter() - t_lookup_start

    if not has_collection:
        logger.error("Could not ensure collection exists in Qdrant. Aborting upsert.")
        return False, lookup_duration, 0.0, 0

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
        if isinstance(vector, (list, tuple)) and len(vector) > 0:
            if all(abs(v) < 1e-12 for v in vector):
                logger.warning(f"Skipping chunk index {i} because vector is essentially zero.")
                continue
        if isinstance(chunk_data, dict) and chunk_data.get("embed") is False:
            logger.warning(f"Skipping chunk index {i} because embed=False flag is set.")
            continue

        pt_index = chunk_indices[i] if chunk_indices is not None else i
        meta = chunk_data.get("metadata", chunk_data) if isinstance(chunk_data, dict) else {}
        chunk_id = chunk_data.get("chunk_id") if isinstance(chunk_data, dict) else None
        if not chunk_id:
            chunk_id = meta.get("chunk_id")
        if not chunk_id:
            chunk_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{pipeline_id}_{file_id}_{pt_index}"))

        point_id = chunk_id

        if isinstance(chunk_data, dict):
            chunk_text = chunk_data.get("text", "")
            section = meta.get("section") or chunk_data.get("section", "unknown")
            content_type = meta.get("content_type") or chunk_data.get("content_type", "paragraph")
            section_path = meta.get("section_path") or chunk_data.get("section_path", "")
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
            semantic_category = meta.get("semantic_category") or chunk_data.get("semantic_category")
            heading_path = meta.get("heading_path") or chunk_data.get("heading_path")
            if isinstance(heading_path, list):
                heading_path = " > ".join(heading_path)
        else:
            chunk_text = str(chunk_data) if chunk_data else ""
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
            semantic_category = None
            heading_path = None

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

        embedding_text = chunk_data.get("embedding_text", chunk_text) if isinstance(chunk_data, dict) else chunk_text
        embedding_hash = hashlib.sha256(embedding_text.encode()).hexdigest()

        payload = {
            "pipeline_id": stored_pipeline_id,
            "file_id": stored_file_id,
            "document_id": stored_file_id,
            "task_id": task_id,
            "chunk_index": pt_index,
            "chunk_text": chunk_text,
            "source_artifact_id": global_meta.get("source_artifact_id") if global_meta else None,
            "original_filename": global_meta.get("original_filename") if global_meta else None,
            "created_at": datetime.utcnow().isoformat(),
            "chunk_id": chunk_id,
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
            "semantic_category": semantic_category,
            "heading_path": heading_path,
            "schema_version": SCHEMA_VERSION,
            "embedding_model": EMBEDDING_MODEL_NAME,
            "embedding_version": EMBEDDING_VERSION,
            "embedding_hash": embedding_hash,
            "filename": global_meta.get("original_filename") if global_meta else None,
        }
        payload = {k: v for k, v in payload.items() if v is not None}

        if chunk_meta_list and i < len(chunk_meta_list):
            c_meta = chunk_meta_list[i]
            if isinstance(c_meta, dict):
                if "metadata" in c_meta and isinstance(c_meta["metadata"], dict):
                    c_meta = c_meta["metadata"]
                for k, v in c_meta.items():
                    if k not in payload or payload.get(k) is None:
                        payload[k] = v

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
        return True, lookup_duration, 0.0, 0

    t_insert_start = time.perf_counter()
    batch_size = getattr(config, 'UPSERT_BATCH_SIZE', 256)
    retries = 0
    last_exception = None
    last_successful_offset = 0
    total_points = len(points)
    overall_inserted = 0   # cumulative across all attempts

    while retries <= UPSERT_MAX_RETRIES:
        attempt_inserted = 0  # for this attempt's logging
        try:
            offset = last_successful_offset
            while offset < total_points:
                batch_points = points[offset:offset + batch_size]
                client.upsert(
                    collection_name=collection_name,
                    points=batch_points,
                    wait=True
                )
                batch_count = len(batch_points)
                attempt_inserted += batch_count
                overall_inserted += batch_count
                last_successful_offset = offset + batch_size
                offset = last_successful_offset

            insertion_duration = time.perf_counter() - t_insert_start
            total_batches = (total_points + batch_size - 1) // batch_size
            logger.info(
                f"Successfully upserted {overall_inserted} total chunks "
                f"(batches {last_successful_offset//batch_size}/{total_batches}) "
                f"to collection {collection_name} (took {insertion_duration:.4f}s)"
            )
            return True, lookup_duration, insertion_duration, overall_inserted

        except Exception as e:
            last_exception = e
            if retries < UPSERT_MAX_RETRIES:
                delay = min(UPSERT_RETRY_DELAY_MAX, UPSERT_RETRY_DELAY_BASE * (2 ** retries))
                current_batch = last_successful_offset // batch_size + 1
                total_batches = (total_points + batch_size - 1) // batch_size
                logger.warning(
                    f"Upsert failed at batch {current_batch}/{total_batches} "
                    f"(offset {last_successful_offset}/{total_points}) "
                    f"(attempt {retries+1}/{UPSERT_MAX_RETRIES+1}): {e}. "
                    f"Retrying from batch {current_batch} in {delay:.2f}s..."
                )
                time.sleep(delay)
                retries += 1
                reset_client()
                client = get_client()
            else:
                logger.error(
                    f"Upsert failed after {UPSERT_MAX_RETRIES+1} attempts. "
                    f"Inserted {overall_inserted} chunks before failure."
                )
                insertion_duration = time.perf_counter() - t_insert_start
                return False, lookup_duration, insertion_duration, overall_inserted

    insertion_duration = time.perf_counter() - t_insert_start
    return False, lookup_duration, insertion_duration, overall_inserted

def search_similar(collection_name, query_vector, top_k=5, filters=None):
    if getattr(config, 'DEBUG_VECTOR_STORE', False):
        print("=" * 80, flush=True)
        print("QDRANT RETRIEVAL COLLECTION NAME:", collection_name, flush=True)
        print("=" * 80, flush=True)
    try:
        ensure_collection(collection_name, config.EMBEDDING_DIMENSION)
        client = get_client()
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
            result = {
                "score": round(hit.score, 4),
                "chunk_text": payload.get("chunk_text"),
                "section": payload.get("section", "unknown"),
                "pipeline_id": payload.get("pipeline_id"),
                "file_id": payload.get("file_id"),
                "document_id": payload.get("document_id"),
                "task_id": payload.get("task_id"),
                "chunk_index": payload.get("chunk_index"),
                "original_filename": payload.get("original_filename"),
                "chunk_id": payload.get("chunk_id"),
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
                "semantic_category": payload.get("semantic_category"),
                "heading_path": payload.get("heading_path"),
                "schema_version": payload.get("schema_version"),
                "embedding_model": payload.get("embedding_model"),
                "embedding_version": payload.get("embedding_version"),
                "embedding_hash": payload.get("embedding_hash"),
                "filename": payload.get("filename"),
                "retrieval_type": "dense",
                "retrieval_backend": "qdrant",
                "retrieval_score": round(hit.score, 4),
            }
            result = {k: v for k, v in result.items() if v is not None}
            results.append(result)
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
            result = {
                "score": 1.0,
                "chunk_text": payload.get("chunk_text"),
                "section": payload.get("section", "unknown"),
                "pipeline_id": payload.get("pipeline_id"),
                "file_id": payload.get("file_id"),
                "document_id": payload.get("document_id"),
                "task_id": payload.get("task_id"),
                "chunk_index": payload.get("chunk_index"),
                "original_filename": payload.get("original_filename"),
                "chunk_id": payload.get("chunk_id"),
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
                "semantic_category": payload.get("semantic_category"),
                "heading_path": payload.get("heading_path"),
                "schema_version": payload.get("schema_version"),
                "embedding_model": payload.get("embedding_model"),
                "embedding_version": payload.get("embedding_version"),
                "embedding_hash": payload.get("embedding_hash"),
                "filename": payload.get("filename"),
                "retrieval_type": "keyword",
                "retrieval_backend": "qdrant_text",
                "retrieval_score": 1.0,
            }
            result = {k: v for k, v in result.items() if v is not None}
            results.append(result)
        return results
    except Exception as e:
        logger.error(f"Failed to search keyword in Qdrant: {e}")
        return []

def get_collection_stats(collection_name="scaleflow_chunks"):
    try:
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

class _ClientProxy:
    def __getattr__(self, name):
        return getattr(get_client(), name)
client = _ClientProxy()