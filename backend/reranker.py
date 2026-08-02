from typing import List, Dict, Any
from services.reranker_service import rerank as service_rerank

class Reranker:
    def __init__(self, top_k: int = 5):
        self.top_k = top_k

    def rerank_candidates(self, query: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not candidates:
            return []

        # 1. Extract texts and chunk items to pass to cross encoder
        # candidates contains {"chunk_id", "text", "sources", "semantic_score", "bm25_score", "graph_score", "graph_depth", "graph_priority", "chunk"}
        flat_chunks = []
        for cand in candidates:
            flat_chunks.append({
                "chunk_id": cand["chunk_id"],
                "chunk_text": cand["text"]
            })

        # Score candidates with the CrossEncoder model
        try:
            scored_flat = service_rerank(query=query, chunks=flat_chunks, top_k=len(flat_chunks))
            scored_map = {item["chunk_id"]: item.get("rerank_score", 0.0) for item in scored_flat}
        except Exception as e:
            print(f"[RERANKER] Model reranking failed, falling back to 0.0 scores: {e}", flush=True)
            scored_map = {cand["chunk_id"]: 0.0 for cand in candidates}

        # 2. Assign scores back to candidates
        for cand in candidates:
            cand["score"] = scored_map.get(cand["chunk_id"], 0.0)

        # 3. Deterministic Sorting:
        # score DESC, graph_priority DESC, semantic_score DESC, bm25_score DESC, chunk_id ASC
        sorted_candidates = sorted(
            candidates,
            key=lambda x: (
                -x.get("score", 0.0),
                -x.get("graph_priority", 0.0),
                -x.get("semantic_score", 0.0),
                -x.get("bm25_score", 0.0),
                x.get("chunk_id", "")
            )
        )

        return sorted_candidates[:self.top_k]
