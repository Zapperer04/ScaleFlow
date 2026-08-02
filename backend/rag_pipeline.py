import time
from typing import List, Dict, Any, Optional
from query_router import QueryRouter
from hybrid_retriever import HybridRetriever
from reranker import Reranker
from context_fusion import ContextFusion
from citation_builder import CitationBuilder
from services.llm_service import get_provider, LLM_PROVIDER_ORDER
from document_graph import DocumentGraph

class RAGPipeline:
    def __init__(self):
        self.query_router = QueryRouter()
        self.hybrid_retriever = HybridRetriever()
        self.reranker = Reranker()
        self.context_fusion = ContextFusion()
        self.citation_builder = CitationBuilder()

    def execute_rag(self, query: str, pipeline_id: int, graph: Optional[DocumentGraph] = None, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start_time = time.perf_counter()
        latencies = {}

        # 1. Intent Detection & Query Routing
        t_route_start = time.perf_counter()
        routing = self.query_router.route_query(query)
        latencies["routing"] = time.perf_counter() - t_route_start

        # 2. Hybrid Retrieval
        t_ret_start = time.perf_counter()
        candidates = self.hybrid_retriever.retrieve(
            query=query,
            pipeline_id=pipeline_id,
            top_k=15,
            filters=filters,
            graph=graph
        )
        latencies["retrieval"] = time.perf_counter() - t_ret_start

        # 3. Reranking
        t_rerank_start = time.perf_counter()
        reranked = self.reranker.rerank_candidates(query, candidates)
        latencies["reranking"] = time.perf_counter() - t_rerank_start

        # 4. Context Fusion
        t_fuse_start = time.perf_counter()
        g_nodes = graph.nodes if graph else []
        fused = self.context_fusion.fuse_context(reranked, g_nodes)
        prompt_context = fused.to_prompt_string()
        latencies["context_fusion"] = time.perf_counter() - t_fuse_start

        # 5. LLM Answer Generation
        t_llm_start = time.perf_counter()
        system_prompt = (
            "You are a precise document Q&A assistant. Answer the user's question using ONLY the provided sources.\n"
            "Strict Grounding Rules:\n"
            "1. Do NOT use external knowledge, infer, or extrapolate beyond the provided sources.\n"
            "2. Cite your sources! Add the citation chunk_id in brackets at the end of the sentence or span that uses it (e.g., [chunk_doc_1]).\n"
            "3. If the sources do not contain direct, explicit information to answer the question, respond: 'The document does not contain sufficient information to answer this question.'"
        )
        user_prompt = f"Sources:\n{prompt_context}\n\nQuestion: {query}\nProvide a precise, grounded answer with citations:"

        answer_text = "The document does not contain sufficient information to answer this question."
        provider_used = "heuristic-fallback"
        
        # Get active provider
        provider = None
        for p_name in LLM_PROVIDER_ORDER:
            provider = get_provider(p_name)
            if provider:
                break
        
        if provider:
            try:
                answer_text, _, _ = provider.generate(system_prompt, user_prompt)
                provider_used = provider.__class__.__name__
            except Exception as e:
                print(f"[RAG PIPELINE] LLM generation failed: {e}. Falling back to heuristic.", flush=True)
                # Fallback to local heuristic
                from services.llm_service import _heuristic_answer
                answer_text, _, _ = _heuristic_answer(query, [cand["chunk"] for cand in reranked])
        else:
            from services.llm_service import _heuristic_answer
            answer_text, _, _ = _heuristic_answer(query, [cand["chunk"] for cand in reranked])

        latencies["llm"] = time.perf_counter() - t_llm_start

        # 6. Citation Building
        t_cit_start = time.perf_counter()
        citations = self.citation_builder.build_citations(answer_text, fused)
        latencies["citation_building"] = time.perf_counter() - t_cit_start

        total_latency = time.perf_counter() - start_time
        latencies["total"] = total_latency

        return {
            "answer": answer_text,
            "intent": routing["intent"],
            "routing": routing,
            "retrieval": {
                "candidates_count": len(candidates),
                "candidates": [
                    {
                        "chunk_id": c["chunk_id"],
                        "sources": c["sources"],
                        "score": c.get("score", 0.0),
                        "semantic_score": c["semantic_score"],
                        "bm25_score": c["bm25_score"],
                        "graph_score": c["graph_score"]
                    } for c in candidates
                ]
            },
            "reranking": {
                "reranked_count": len(reranked),
                "reranked_chunks": [
                    {
                        "chunk_id": r["chunk_id"],
                        "score": r.get("score", 0.0),
                        "sources": r["sources"]
                    } for r in reranked
                ]
            },
            "context": fused.to_dict(),
            "citations": citations,
            "latency": latencies,
            "provider_used": provider_used
        }
