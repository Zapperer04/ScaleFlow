import time
from typing import List, Dict, Any

from services.document_retrieval.orchestrator import RetrievalOrchestrator
from services.document_retrieval.evaluation.dataset_loader import DatasetLoader
from services.document_retrieval.evaluation.retrieval_logger import RetrievalLogger

class BenchmarkRunner:
    def __init__(self, orchestrator: RetrievalOrchestrator = None, loader: DatasetLoader = None):
        self.orchestrator = orchestrator or RetrievalOrchestrator()
        self.loader = loader or DatasetLoader()
        self.logger = RetrievalLogger()

    def run_benchmark(self) -> List[Dict[str, Any]]:
        questions = self.loader.load_questions()
        if not questions:
            return []

        benchmark_results = []
        for q_data in questions:
            query = q_data["question"]
            doc_id = q_data["document_id"]

            start_time = time.time()
            res = self.orchestrator.retrieve(query, doc_id)
            latency = time.time() - start_time

            final_context = res["final_context"]
            retrieved_chunks = [c.chunk_id for c in final_context]
            
            # Aggregate nodes, tables, entities
            retrieved_nodes = []
            retrieved_entities = []
            retrieved_tables = []
            for c in final_context:
                retrieved_nodes.extend(c.graph_node_ids)
                retrieved_entities.extend(c.entities)
                if c.metadata.get("table_ref"):
                    retrieved_tables.append(c.metadata["table_ref"])

            # Calculate token count
            token_count = sum(len(c.text.split()) for c in final_context) * 4 // 3

            # Agreement score calculation
            agreement_count = sum(
                1 for c in final_context if len(c.metadata.get("confidence_breakdown", {}).get("sources", [])) > 1
            )

            # Log execution E2E
            self.logger.log_run(
                query=query,
                experts=list(res["latencies"]["experts"].keys()),
                evidence_count=len(retrieved_chunks),
                expanded_evidence_count=len(retrieved_nodes),
                candidate_count=len(final_context),
                fusion_score=sum(c.score for c in final_context) / len(final_context) if final_context else 0.0,
                agreement_score=float(agreement_count),
                final_ranking=retrieved_chunks,
                latency=latency,
                tokens=token_count
            )

            benchmark_results.append({
                "question_data": q_data,
                "retrieved_chunks": retrieved_chunks,
                "retrieved_nodes": retrieved_nodes,
                "retrieved_entities": retrieved_entities,
                "retrieved_tables": retrieved_tables,
                "latency": latency,
                "token_usage": token_count,
                "agreement_count": agreement_count,
                "latency_details": res["latencies"]
            })

        return benchmark_results
