import os
import sys

# Adjust path to find config and services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from services.vector_store import search_similar

def retrieve_context(query_vector: list, pipeline_id: int, top_k: int = None, query: str = "") -> dict:
    """
    Retrieve semantic context chunks from vector store.
    
    Parameters
    ----------
    query_vector : dense vector representation of the query
    pipeline_id  : document-scoped filter constraint
    top_k        : number of results to fetch
    query        : optional original query text
    
    Returns
    -------
    Dictionary of retrieval results.
    """
    if top_k is None:
        top_k = config.DEFAULT_RETRIEVAL_TOP_K
        
    filters = {"pipeline_id": pipeline_id}
    
    # Qdrant similarity search
    results = search_similar("scaleflow_chunks", query_vector, top_k=top_k, filters=filters)
    
    # Filter by MIN_RETRIEVAL_SCORE
    min_score = config.MIN_RETRIEVAL_SCORE
    filtered_results = [r for r in results if float(r.get("score") or 0.0) >= min_score or r.get("chunk_index") == -1]
    
    # Fallback: if scoped to a specific pipeline and nothing passed, bypass threshold
    if not filtered_results and results:
        filtered_results = results
        
    return {
        "query": query,
        "results": filtered_results
    }
