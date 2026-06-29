import os
import sys

# Adjust path to find config and services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from services.vector_store import search_similar, search_keyword

def retrieve_context(query_vector: list, pipeline_id: int, top_k: int = None, query: str = "") -> dict:
    """
    Retrieve semantic context chunks from vector store.
    Delegates to retrieve_and_rerank to get the benefits of multi-collection search,
    deduplication, and reranking.
    """
    if top_k is None:
        top_k = config.DEFAULT_RETRIEVAL_TOP_K
        
    return retrieve_and_rerank(query_vector=query_vector, pipeline_id=pipeline_id, top_k=top_k, query=query)

from services.reranker_service import rerank

def detect_query_intent(query: str) -> list[str]:
    # Cleaned up: remove all keyword-driven collection routing. Search all relevant collections uniformly.
    return [config.QDRANT_PARAGRAPH_COLLECTION, config.QDRANT_TABLE_COLLECTION]

def retrieve_and_rerank(query_vector: list, pipeline_id: int, top_k: int = 5, query: str = "") -> dict:
    """
    Retrieve and rerank retrieved chunks.
    pipeline_id=None performs a global search across all indexed documents.
    """
    collections = detect_query_intent(query)
    
    # Print search collections log for worker telemetry / visibility
    print(f"[RETRIEVAL] SEARCHING COLLECTIONS: {collections} for query: '{query}'", flush=True)
    
    # Only filter by pipeline_id when explicitly provided
    filters = {"pipeline_id": pipeline_id} if pipeline_id is not None else None

    all_candidates = []
    candidate_recall_limit = max(top_k * 5, 30)

    for collection in collections:
        # 1. Dense vector search
        vector_results = search_similar(
            collection_name=collection,
            query_vector=query_vector,
            top_k=candidate_recall_limit,
            filters=filters
        )
        all_candidates.extend(vector_results)

        # 2. Sparse keyword search
        if query:
            keyword_results = search_keyword(
                collection_name=collection,
                query_text=query,
                top_k=candidate_recall_limit,
                filters=filters
            )
            all_candidates.extend(keyword_results)
    
    if not all_candidates:
        return {
            "query": query,
            "results": []
        }
    
    # Deduplicate by normalized text content or point/chunk index
    seen = set()
    unique_candidates = []
    for c in all_candidates:
        text_content = (c.get("chunk_text") or c.get("text") or "").strip()
        # Also key by file_id + chunk_index to ensure uniqueness if text is identical but from different locations
        c_key = (c.get("file_id"), c.get("chunk_index"), text_content)
        if c_key not in seen:
            seen.add(c_key)
            unique_candidates.append(c)
    
    # Step 3: Rerank the high-recall pool
    reranked = rerank(query, unique_candidates, top_k=top_k)
    
    return {
        "query": query,
        "results": reranked
    }


