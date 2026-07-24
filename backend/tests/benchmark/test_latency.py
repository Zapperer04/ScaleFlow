import pytest
import time
import os
import sys

# Ensure backend directory is in path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from engine.document_retrieval.orchestrator import RetrievalOrchestrator
from engine.document_retrieval.query_understanding import QueryUnderstanding

class MockStore:
    def __init__(self):
        self.db = {
            "embeddings/vectors.json": [{"chunk_id": "chunk-0", "vector": [0.1] * 768, "metadata": {"type": "chunk"}}],
            "graph/nodes.json": [],
            "graph/edges.json": [],
            "entities/entities.json": {},
            "tables/tables.json": [],
            "layout/layout.json": {},
            "chunks/chunks.json": [
                {
                    "chunk_id": "chunk-0",
                    "text": "This is test text for latency measurement.",
                    "graph_node_ids": ["node-h1"],
                    "entities": [],
                    "page_range": [1],
                    "best_for": ["semantic"]
                }
            ]
        }
    def load_json(self, doc_id, rel_path):
        return self.db.get(rel_path)

def test_retrieval_latency_instrumentation(monkeypatch):
    # Mock embedding generator
    import engine.document_retrieval.query_understanding as qu_mod
    monkeypatch.setattr(qu_mod, "embed_text", lambda text: [0.1] * 768)

    store = MockStore()
    orchestrator = RetrievalOrchestrator(store=store)

    start = time.time()
    res = orchestrator.retrieve("test query for latency", "doc123")
    total_elapsed = time.time() - start

    assert "latencies" in res
    latencies = res["latencies"]
    assert "experts" in latencies
    assert "fusion" in latencies
    assert "rerank" in latencies
    assert "optimizer" in latencies
    assert "total" in latencies
    assert latencies["total"] <= total_elapsed
