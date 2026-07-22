import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.document_pipeline.storage.storage import DocumentStore
from services.document_retrieval.orchestrator import RetrievalOrchestrator

class MockStore:
    def __init__(self):
        self.db = {
            "embeddings/vectors.json": [
                {"chunk_id": "chunk-0", "vector": [0.1] * 768, "metadata": {"type": "chunk"}},
                {"chunk_id": "node-h1", "vector": [0.9] * 768, "metadata": {"type": "heading"}}
            ],
            "graph/nodes.json": [
                {"id": "node-h1", "type": "Heading", "text": "Introduction"},
                {"id": "node-p1", "type": "Paragraph", "text": "This relates to Table 1"}
            ],
            "graph/edges.json": [
                {"source": "node-h1", "target": "node-p1", "type": "parent_child"}
            ],
            "entities/entities.json": {
                "entities": [
                    {
                        "id": "ent-1",
                        "name": "Google",
                        "type": "Organization",
                        "normalized_value": "Google",
                        "aliases": ["Google Corp"],
                        "graph_node_ids": ["node-p1"]
                    }
                ],
                "edges": []
            },
            "tables/tables.json": [
                {
                    "id": "tbl-1",
                    "caption": "Table 1",
                    "headers": ["A", "B"],
                    "graph_node_id": "node-p1"
                }
            ],
            "layout/layout.json": {
                "visual_blocks": {
                    "node-p1": {
                        "page": 1,
                        "type": "paragraph",
                        "bbox": {"ymin": 0.8, "xmin": 0.8, "ymax": 0.9, "xmax": 0.9}
                    }
                }
            },
            "chunks/chunks.json": [
                {
                    "chunk_id": "chunk-0",
                    "text": "This is standard introduction text.",
                    "graph_node_ids": ["node-h1", "node-p1"],
                    "entities": ["Google"],
                    "page_range": [1],
                    "best_for": ["semantic"],
                    "importance_score": 1.2
                }
            ]
        }

    def load_json(self, doc_id, rel_path):
        return self.db.get(rel_path)

def test_retrieval_orchestrator_e2e():
    store = MockStore()
    orchestrator = RetrievalOrchestrator(store=store)
    
    # E2E Esemble retrieval execution
    response = orchestrator.retrieve("Compare row values in Table 1 for Google Corp", doc_id="doc123")
    
    assert "query" in response
    assert len(response["final_context"]) > 0
    assert response["final_context"][0].chunk_id.startswith("chunk-0")
    
    # Verify latencies exist
    assert "fusion" in response["latencies"]
    assert "experts" in response["latencies"]
    assert "total" in response["latencies"]

def test_retrieval_orchestrator_session_memory_and_multihop():
    store = MockStore()
    orchestrator = RetrievalOrchestrator(store=store)
    
    # Enable session id
    session_id = "test-session-123"
    
    # 1. Retrieve first turn
    res1 = orchestrator.retrieve("Find Google metrics", doc_id="doc123", session_id=session_id)
    assert len(res1["final_context"]) > 0
    
    # Verify memory is updated
    mem = orchestrator.session_memory.get_memory(session_id)
    assert "chunk-0" in mem["chunk_ids"]
    
    # 2. Retrieve second turn utilizing memory context and triggering multi-hop (force high multi_hop probability)
    # Mock analyzer to return high multi_hop_probability
    original_analyze = orchestrator.query_analyzer.analyze
    def mock_analyze(q):
        qu = original_analyze(q)
        qu.multi_hop_probability = 0.8
        return qu
    orchestrator.query_analyzer.analyze = mock_analyze
    
    res2 = orchestrator.retrieve("Explain the correlation comparison", doc_id="doc123", session_id=session_id)
    assert len(res2["final_context"]) > 0
    # Hop 2 latency keys should be present in expert latencies
    assert any("hop2" in k for k in res2["latencies"]["experts"])
