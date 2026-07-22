from typing import List, Dict, Any, Optional
from engine.document_retrieval.orchestrator import RetrievalOrchestrator
from backend.platform.cache.retrieval_cache import RetrievalCache

class RetrievalService:
    def __init__(self):
        # Initialize engine retrieval orchestrator
        self.orchestrator = RetrievalOrchestrator()
        self.cache = RetrievalCache()

    def retrieve(
        self,
        query: str,
        document_id: str,
        top_k: int = 5,
        token_limit: int = 4000,
        session_id: str = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        params = {"top_k": top_k, "token_limit": token_limit, "document_id": document_id}
        
        # 1. Attempt cache lookup
        if use_cache:
            cached_data = self.cache.get_context(query_embedding=None, query_text=query, params=params)
            if cached_data:
                # Reconstruct Candidates from cached dictionary
                from engine.document_retrieval.candidate import Candidate
                candidates = []
                for c in cached_data:
                    candidates.append(Candidate(
                        chunk_id=c["chunk_id"],
                        text=c["text"],
                        score=c["score"],
                        entities=c.get("entities", []),
                        graph_node_ids=c.get("graph_node_ids", []),
                        section_path=c.get("section_path", []),
                        metadata=c.get("metadata", {})
                    ))
                return {
                    "query": query,
                    "final_context": candidates,
                    "cached": True,
                    "confidence_distribution": {"overall": 0.8},
                    "latencies": {"total": 0.001}
                }

        # 2. Run retrieval engine
        result = self.orchestrator.retrieve(
            query=query,
            doc_id=document_id,
            top_k=top_k,
            token_limit=token_limit,
            session_id=session_id
        )

        # 3. Cache the context
        if use_cache:
            serialized_candidates = []
            for c in result["final_context"]:
                serialized_candidates.append({
                    "chunk_id": c.chunk_id,
                    "text": c.text,
                    "score": c.score,
                    "entities": c.entities,
                    "graph_node_ids": c.graph_node_ids,
                    "section_path": c.section_path,
                    "metadata": c.metadata
                })
            self.cache.cache_context(query_embedding=None, query_text=query, params=params, candidates=serialized_candidates)

        return result
