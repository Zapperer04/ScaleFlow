import time
import concurrent.futures
from typing import List, Dict, Any

from engine.document_pipeline.storage.storage import DocumentStore
from engine.document_retrieval.query_understanding import QueryAnalyzer, QueryUnderstanding
from engine.document_retrieval.evidence import Evidence
from engine.document_retrieval.evidence_expander import EvidenceExpander
from engine.document_retrieval.candidate_builder import CandidateBuilder
from engine.document_retrieval.fusion import FusionEngine
from engine.document_retrieval.reranker import CrossEncoderReranker
from engine.document_retrieval.context_optimizer import ContextOptimizer
from engine.document_retrieval.confidence import ConfidenceCalibrator
from engine.document_retrieval.retrieval_metrics import RetrievalMetricsCollector

from engine.document_retrieval.experts.vector_expert import VectorExpert
from engine.document_retrieval.experts.graph_expert import GraphExpert
from engine.document_retrieval.experts.entity_expert import EntityExpert
from engine.document_retrieval.experts.table_expert import TableExpert
from engine.document_retrieval.experts.layout_expert import LayoutExpert
from engine.document_retrieval.retrieval_memory import RetrievalSessionMemory

class RetrievalOrchestrator:
    def __init__(self, store: DocumentStore = None):
        self.store = store or DocumentStore()
        self.query_analyzer = QueryAnalyzer()
        self.evidence_expander = EvidenceExpander()
        self.candidate_builder = CandidateBuilder()
        self.fusion_engine = FusionEngine()
        self.reranker = CrossEncoderReranker()
        self.context_optimizer = ContextOptimizer()
        self.confidence_calibrator = ConfidenceCalibrator()
        self.metrics_collector = RetrievalMetricsCollector()
        self.session_memory = RetrievalSessionMemory()

        # Initialize parallel experts
        self.experts = [
            VectorExpert(),
            GraphExpert(),
            EntityExpert(),
            TableExpert(),
            LayoutExpert()
        ]

    def retrieve(self, query: str, doc_id: str, top_k: int = 5, token_limit: int = 4000, session_id: str = None) -> Dict[str, Any]:
        start_time = time.time()
        
        # Load memory context if session_id is provided
        memory_evidence = []
        if session_id:
            mem = self.session_memory.get_memory(session_id)
            # Add past memory targets directly as seeds in evidence pool
            for chunk_id in mem.chunk_ids:
                memory_evidence.append(Evidence(
                    id=chunk_id,
                    source="memory",
                    evidence_type="chunk",
                    score=0.8,
                    confidence=0.8,
                    metadata={
                        "chunk_id": chunk_id,
                        "reason": "Retrieved from conversation session memory context"
                    }
                ))

        # 1. Query Understanding
        qu = self.query_analyzer.analyze(query)

        # 2. Parallel Experts execution
        evidence_pool: List[Evidence] = []
        expert_latencies = {}

        def run_expert(expert):
            exp_start = time.time()
            try:
                results = expert.retrieve(qu, doc_id, self.store)
            except Exception as e:
                results = []
            latency = time.time() - exp_start
            return expert.name, results, latency

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_expert = {executor.submit(run_expert, exp): exp for exp in self.experts}
            for future in concurrent.futures.as_completed(future_to_expert):
                name, results, latency = future.result()
                evidence_pool.extend(results)
                expert_latencies[name] = latency

        # E2E Multi-Hop second pass check
        if qu.multi_hop_probability > 0.5:
            # Extract additional entity/structural context seeds from 1st pass to expand search
            second_hop_keywords = []
            for ev in evidence_pool:
                reason = ev.metadata.get("reason")
                if reason:
                    second_hop_keywords.append(reason.split()[-1])
            
            # Enrich copy of query understanding
            qu.keywords = list(set(qu.keywords + second_hop_keywords[:5]))
            
            # Re-execute parallel experts for 2nd hop
            second_pool = []
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future_to_expert = {executor.submit(run_expert, exp): exp for exp in self.experts}
                for future in concurrent.futures.as_completed(future_to_expert):
                    name, results, latency = future.result()
                    second_pool.extend(results)
                    expert_latencies[f"{name}_hop2"] = latency
            evidence_pool.extend(second_pool)

        # Merge memory evidence context if any
        if memory_evidence:
            evidence_pool.extend(memory_evidence)

        # 3. Evidence Expansion
        exp_start = time.time()
        expanded_evidence = self.evidence_expander.expand(evidence_pool, doc_id, self.store)
        expansion_latency = time.time() - exp_start

        # 4. Candidate Builder
        cb_start = time.time()
        candidates = self.candidate_builder.build_candidates(expanded_evidence, doc_id, self.store)
        candidate_latency = time.time() - cb_start

        # 5. Fusion Engine
        fusion_start = time.time()
        fused = self.fusion_engine.fuse_candidates(candidates, qu)
        fusion_latency = time.time() - fusion_start

        # 6. Reranking
        rerank_start = time.time()
        reranked = self.reranker.rerank_candidates(query, fused, top_k=top_k * 3)
        rerank_latency = time.time() - rerank_start

        # 7. Context Optimization
        opt_start = time.time()
        final_context = self.context_optimizer.optimize_context(reranked, token_limit=token_limit)
        optimizer_latency = time.time() - opt_start

        # Save session memory turn if session_id is provided
        if session_id:
            retrieved_chunk_ids = [c.chunk_id for c in final_context]
            retrieved_node_ids = []
            for c in final_context:
                retrieved_node_ids.extend(c.graph_node_ids)
            retrieved_entities = []
            for c in final_context:
                retrieved_entities.extend(c.entities)
            retrieved_sections = []
            for c in final_context:
                retrieved_sections.extend(c.section_path or [])
            retrieved_tables = []
            for c in final_context:
                tbl = c.metadata.get("table")
                if tbl and tbl.get("id"):
                    retrieved_tables.append(tbl["id"])

            self.session_memory.add_turn(
                session_id=session_id,
                chunk_ids=retrieved_chunk_ids,
                node_ids=retrieved_node_ids,
                entity_ids=retrieved_entities,
                answer="",
                document_id=doc_id,
                sections=retrieved_sections,
                tables=retrieved_tables,
                query=query
            )

        # 8. Calibration & Metrics Logging
        total_latency = time.time() - start_time
        confidence_distribution = self.confidence_calibrator.calibrate(expanded_evidence)

        # Count representation agreements (chunks retrieved by multiple experts)
        agreement_count = sum(
            1 for c in fused if len(c.metadata.get("confidence_breakdown", {}).get("sources", [])) > 1
        )

        final_token_estimate = sum(len(c.text.split()) for c in final_context) * 4 // 3

        self.metrics_collector.log_metrics(
            query=query,
            expert_latencies=expert_latencies,
            fusion_latency=fusion_latency,
            rerank_latency=rerank_latency,
            optimizer_latency=optimizer_latency,
            total_latency=total_latency,
            candidate_count=len(candidates),
            evidence_count=len(expanded_evidence),
            agreement_count=agreement_count,
            final_token_count=final_token_estimate,
            confidence_distribution=confidence_distribution
        )

        return {
            "query": query,
            "query_understanding": qu,
            "final_context": final_context,
            "confidence_distribution": confidence_distribution,
            "latencies": {
                "experts": expert_latencies,
                "fusion": fusion_latency,
                "rerank": rerank_latency,
                "optimizer": optimizer_latency,
                "total": total_latency
            }
        }
