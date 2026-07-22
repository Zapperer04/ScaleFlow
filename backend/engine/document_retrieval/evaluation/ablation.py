import time
from typing import List, Dict, Any

from engine.document_retrieval.orchestrator import RetrievalOrchestrator
from engine.document_retrieval.experts.vector_expert import VectorExpert
from engine.document_retrieval.experts.graph_expert import GraphExpert
from engine.document_retrieval.experts.entity_expert import EntityExpert
from engine.document_retrieval.experts.table_expert import TableExpert
from engine.document_retrieval.experts.layout_expert import LayoutExpert
from engine.document_retrieval.evaluation.metrics import MetricsCalculator

class AblationStudyRunner:
    def __init__(self, orchestrator: RetrievalOrchestrator = None):
        self.orchestrator = orchestrator or RetrievalOrchestrator()
        self.metrics_calculator = MetricsCalculator()

        # Define configurations
        self.configs = {
            "Vector-Only": [VectorExpert()],
            "Graph-Only": [GraphExpert()],
            "Entity-Only": [EntityExpert()],
            "Table-Only": [TableExpert()],
            "Layout-Only": [LayoutExpert()],
            "Hybrid": [VectorExpert(), GraphExpert(), EntityExpert(), TableExpert(), LayoutExpert()]
        }

    def run_ablation_on_query(self, query: str, doc_id: str, expected_chunks: List[str], expected_nodes: List[str], expected_entities: List[str], expected_tables: List[str]) -> Dict[str, Dict[str, Any]]:
        results = {}
        original_experts = list(self.orchestrator.experts)

        try:
            for name, experts in self.configs.items():
                # Temporarily replace experts list in orchestrator
                self.orchestrator.experts = experts

                start_time = time.time()
                retrieval_res = self.orchestrator.retrieve(query, doc_id)
                latency = time.time() - start_time

                final_context = retrieval_res["final_context"]
                retrieved_chunks = [c.chunk_id for c in final_context]
                
                # Collect retrieved entities, nodes, and tables from metadata
                retrieved_nodes = []
                retrieved_entities = []
                retrieved_tables = []
                for cand in final_context:
                    retrieved_nodes.extend(cand.graph_node_ids)
                    retrieved_entities.extend(cand.entities)
                    # Extract tables from metadata
                    table_ref = cand.metadata.get("table_ref")
                    if table_ref:
                        retrieved_tables.append(table_ref)

                metrics = self.metrics_calculator.calculate_all(
                    retrieved_chunks=retrieved_chunks,
                    expected_chunks=expected_chunks,
                    retrieved_nodes=retrieved_nodes,
                    expected_nodes=expected_nodes,
                    retrieved_entities=retrieved_entities,
                    expected_entities=expected_entities,
                    retrieved_tables=retrieved_tables,
                    expected_tables=expected_tables
                )

                # Count final token estimates
                token_count = sum(len(c.text.split()) for c in final_context) * 4 // 3

                results[name] = {
                    "latency": latency,
                    "token_usage": token_count,
                    "metrics": metrics,
                    "retrieved_chunk_count": len(retrieved_chunks)
                }
        finally:
            # Restore original experts
            self.orchestrator.experts = original_experts

        return results
