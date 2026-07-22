import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from engine.document_retrieval.evaluation.ablation import AblationStudyRunner
from engine.document_retrieval.orchestrator import RetrievalOrchestrator

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

def test_ablation_study_runner(monkeypatch):
    import engine.document_retrieval.query_understanding as qu_mod
    monkeypatch.setattr(qu_mod, "embed_text", lambda text: [0.1] * 768)

    store = MockStore()
    orchestrator = RetrievalOrchestrator(store=store)
    ablation = AblationStudyRunner(orchestrator=orchestrator)
    
    res = ablation.run_ablation_on_query(
        query="What is Table 1?",
        doc_id="doc123",
        expected_chunks=["chunk-0"],
        expected_nodes=[],
        expected_entities=[],
        expected_tables=[]
    )
    
    assert "Vector-Only" in res
    assert "Hybrid" in res
    assert res["Vector-Only"]["metrics"]["recall_5"] == 1.0
