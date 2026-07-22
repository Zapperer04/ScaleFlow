from typing import List
from engine.document_retrieval.candidate import Candidate

try:
    from services.reranker_service import rerank
    RERANKER_AVAILABLE = True
except ImportError:
    RERANKER_AVAILABLE = False

class CrossEncoderReranker:
    def rerank_candidates(self, query: str, candidates: List[Candidate], top_k: int = 10) -> List[Candidate]:
        if not candidates:
            return []

        if RERANKER_AVAILABLE:
            try:
                # Convert candidates to list of dicts to match rerank signature
                candidates_dicts = []
                for c in candidates:
                    d = c.__dict__.copy()
                    # Make sure rerank can read text
                    d["text"] = c.text
                    candidates_dicts.append(d)

                reranked_dicts = rerank(query, candidates_dicts, top_k=top_k)

                # Map back to Candidate objects
                reranked_candidates = []
                # Keep track of mapping
                chunk_to_cand = {c.chunk_id: c for c in candidates}
                for rd in reranked_dicts:
                    c_id = rd.get("chunk_id")
                    if c_id in chunk_to_cand:
                        cand = chunk_to_cand[c_id]
                        # Update score with reranker score
                        cand.score = rd.get("score", cand.score)
                        reranked_candidates.append(cand)
                return reranked_candidates
            except Exception:
                pass

        # Fallback: Sort by candidate score
        candidates.sort(key=lambda x: x.score, reverse=True)
        return candidates[:top_k]
