from typing import List, Dict, Any
from engine.document_retrieval.orchestrator import RetrievalOrchestrator
from engine.document_retrieval.evaluation.dataset_loader import DatasetLoader
from engine.document_retrieval.evaluation.benchmark_runner import BenchmarkRunner
from engine.document_retrieval.evaluation.ablation import AblationStudyRunner
from engine.document_retrieval.evaluation.metrics import MetricsCalculator

class RetrievalEvaluator:
    def __init__(self, orchestrator: RetrievalOrchestrator = None):
        self.orchestrator = orchestrator or RetrievalOrchestrator()
        self.loader = DatasetLoader()
        self.runner = BenchmarkRunner(self.orchestrator, self.loader)
        self.ablation_runner = AblationStudyRunner(self.orchestrator)
        self.metrics_calculator = MetricsCalculator()

    def evaluate_all(self) -> Dict[str, Any]:
        # 1. Run Benchmark
        results = self.runner.run_benchmark()
        
        # 2. Run Ablation and compute scores E2E
        ablation_results = {}
        overall_metrics = []

        for res in results:
            q_data = res["question_data"]
            ab_res = self.ablation_runner.run_ablation_on_query(
                query=q_data["question"],
                doc_id=q_data["document_id"],
                expected_chunks=q_data["expected_chunk_ids"],
                expected_nodes=q_data["expected_graph_nodes"],
                expected_entities=q_data["expected_entities"],
                expected_tables=q_data["expected_tables"]
            )
            ablation_results[q_data["question"]] = ab_res

            # Calculate metrics for hybrid (which was run inside runner)
            metrics = self.metrics_calculator.calculate_all(
                retrieved_chunks=res["retrieved_chunks"],
                expected_chunks=q_data["expected_chunk_ids"],
                retrieved_nodes=res["retrieved_nodes"],
                expected_nodes=q_data["expected_graph_nodes"],
                retrieved_entities=res["retrieved_entities"],
                expected_entities=q_data["expected_entities"],
                retrieved_tables=res["retrieved_tables"],
                expected_tables=q_data["expected_tables"]
            )
            overall_metrics.append(metrics)

        # Average metrics
        avg_metrics = {}
        if overall_metrics:
            for key in overall_metrics[0].keys():
                avg_metrics[key] = sum(m[key] for m in overall_metrics) / len(overall_metrics)

        return {
            "benchmark_results": results,
            "ablation_results": ablation_results,
            "overall_metrics": avg_metrics
        }
