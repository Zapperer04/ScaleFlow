import time
import concurrent.futures
from typing import List, Dict, Any

from services.document_pipeline.storage.storage import DocumentStore
from services.document_retrieval.query_understanding import QueryAnalyzer, QueryUnderstanding
from services.document_retrieval.evidence import Evidence
from services.document_retrieval.evidence_expander import EvidenceExpander
from services.document_retrieval.candidate_builder import CandidateBuilder
from services.document_retrieval.fusion import FusionEngine
from services.document_retrieval.reranker import CrossEncoderReranker
from services.document_retrieval.context_optimizer import ContextOptimizer
from services.document_retrieval.confidence import ConfidenceCalibrator
from services.document_retrieval.retrieval_metrics import RetrievalMetricsCollector

from services.document_retrieval.experts.vector_expert import VectorExpert
from services.document_retrieval.experts.graph_expert import GraphExpert
from services.document_retrieval.experts.entity_expert import EntityExpert
from services.document_retrieval.experts.table_expert import TableExpert
from services.document_retrieval.experts.layout_expert import LayoutExpert

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

        # Initialize parallel experts
        self.experts = [
            VectorExpert(),
            GraphExpert(),
            EntityExpert(),
            TableExpert(),
            LayoutExpert()
        ]

    def retrieve(self, query: str, doc_id: str, top_k: int = 5, token_limit: int = 4000) -> Dict[str, Any]:
        start_time = time.time()
        
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
