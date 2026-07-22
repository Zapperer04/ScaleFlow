import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from services.document_retrieval.evaluation.evaluator import RetrievalEvaluator
from services.document_retrieval.orchestrator import RetrievalOrchestrator

class MockStore:
    def __init__(self):
        self.db = {
            "embeddings/vectors.json": [
                {"chunk_id": "chunk-0", "vector": [0.1] * 768, "metadata": {"type": "chunk"}}
            ],
            "graph/nodes.json": [],
            "graph/edges.json": [],
            "entities/entities.json": {},
            "tables/tables.json": [],
            "layout/layout.json": {},
            "chunks/chunks.json": [
                {
                    "chunk_id": "chunk-0",
                    "text": "Introduction text.",
                    "graph_node_ids": ["node-h1"],
                    "entities": ["Google"],
                    "page_range": [1],
                    "best_for": ["semantic"]
                }
            ]
        }
    def load_json(self, doc_id, rel_path):
        return self.db.get(rel_path)

def test_evaluator_e2e_flow(monkeypatch):
    import services.document_retrieval.query_understanding as qu_mod
    monkeypatch.setattr(qu_mod, "embed_text", lambda text: [0.1] * 768)

    store = MockStore()
    orchestrator = RetrievalOrchestrator(store=store)
    
    evaluator = RetrievalEvaluator(orchestrator=orchestrator)
    
    # Mock loader to return mock E2E questions list
    def mock_load_questions(self):
        return [
            {
                "question": "What is Table 1?",
                "document_id": "doc123",
                "expected_chunk_ids": ["chunk-0"],
                "expected_graph_nodes": [],
                "expected_entities": [],
                "expected_tables": [],
                "category": "Technical Manuals"
            }
        ]
        
    from services.document_retrieval.evaluation.dataset_loader import DatasetLoader
    monkeypatch.setattr(DatasetLoader, "load_questions", mock_load_questions)
    
    eval_data = evaluator.evaluate_all()
    assert "overall_metrics" in eval_data
    assert eval_data["overall_metrics"]["recall_5"] == 1.0
    assert "benchmark_results" in eval_data
    assert "ablation_results" in eval_data
