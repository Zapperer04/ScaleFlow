import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from engine.document_retrieval.evaluation.benchmark_runner import BenchmarkRunner
from engine.document_retrieval.evaluation.dataset_loader import DatasetLoader
from engine.document_retrieval.orchestrator import RetrievalOrchestrator

class MockDatasetLoader:
    def load_questions(self):
        return [
            {
                "question": "What is Table 1 about?",
                "document_id": "doc123",
                "expected_chunk_ids": ["chunk-0"],
                "expected_graph_nodes": ["node-p1"],
                "expected_entities": ["Google"],
                "expected_tables": ["tbl-1"],
                "category": "Technical Manuals"
            }
        ]

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
                    "text": "Introduction chunk mentioning Table 1.",
                    "graph_node_ids": ["node-h1"],
                    "entities": ["Google"],
                    "page_range": [1],
                    "best_for": ["semantic"]
                }
            ]
        }
    def load_json(self, doc_id, rel_path):
        return self.db.get(rel_path)

def test_benchmark_runner(monkeypatch):
    import engine.document_retrieval.query_understanding as qu_mod
    monkeypatch.setattr(qu_mod, "embed_text", lambda text: [0.1] * 768)

    store = MockStore()
    orchestrator = RetrievalOrchestrator(store=store)
    loader = MockDatasetLoader()
    
    runner = BenchmarkRunner(orchestrator=orchestrator, loader=loader)
    results = runner.run_benchmark()
    
    assert len(results) == 1
    assert results[0]["retrieved_chunks"] == ["chunk-0"]
    assert results[0]["latency"] > 0.0
