import os
import uuid
import logging
from datetime import datetime
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

logger = logging.getLogger(__name__)

QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", 6333))

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Initialize client
if os.environ.get("DB_MODE") == "sqlite":
    logger.info("SQLite mode detected: Using in-memory QdrantClient fallback")
    client = QdrantClient(location=":memory:")
else:
    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=3.0)
        client.get_collections()
    except Exception as e:
        logger.warning(f"Could not connect to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}: {e}. Falling back to in-memory QdrantClient.")
        client = QdrantClient(location=":memory:")

def ensure_collection(collection_name="scaleflow_chunks", vector_size=None):
    if vector_size is None:
        vector_size = config.EMBEDDING_DIMENSION
    try:
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
        return True
    except Exception as e:
        logger.error(f"Failed to ensure Qdrant collection {collection_name}: {e}")
        return False

def upsert_document_chunks(pipeline_id, file_id, task_id, chunks, vectors, metadata=None):
    collection_name = "scaleflow_chunks"
    
    print("=" * 80, flush=True)
    print("QDRANT INSERTION COLLECTION NAME:", collection_name, flush=True)
    print("=" * 80, flush=True)

    import time
    t_lookup_start = time.perf_counter()
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
        payload = {
            "pipeline_id": pipeline_id,
            "file_id": file_id,
            "task_id": task_id,
            "chunk_index": i,
            "chunk_text": chunk_text,
            "source_artifact_id": global_meta.get("source_artifact_id") if global_meta else None,
            "original_filename": global_meta.get("original_filename") if global_meta else None,
            "created_at": datetime.utcnow().isoformat(),
            
            # Compatibility keys for step 3
            "document_id": file_id,
            "filename": global_meta.get("original_filename") if global_meta else None,
            "chunk_id": i,
            "text": chunk_text
        }
        
        # Merge chunk-specific metadata fields
        if chunk_meta_list and i < len(chunk_meta_list):
            c_meta = chunk_meta_list[i]
            if isinstance(c_meta, dict):
                payload.update(c_meta)
        
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
        # Build filter if present
        q_filter = None
        if filters:
            conditions = []
            for key, val in filters.items():
                if val is not None:
                    conditions.append(
                        qmodels.FieldCondition(
                            key=key,
                            match=qmodels.MatchValue(value=val)
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
