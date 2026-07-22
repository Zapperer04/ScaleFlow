import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.document_retrieval.evidence import Evidence
from services.document_retrieval.candidate_builder import CandidateBuilder

class MockStore:
    def __init__(self):
        self.db = {
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
            ],
            "layout/layout.json": {}
        }
    def load_json(self, doc_id, rel_path):
        return self.db.get(rel_path)

def test_candidate_builder():
    store = MockStore()
    builder = CandidateBuilder()
    
    evidence_list = [
        Evidence(
            id="ev-1",
            source="graph",
            evidence_type="node",
            score=0.9,
            confidence=0.8,
            graph_node_ids=["node-h1"]
        )
    ]
    
    candidates = builder.build_candidates(evidence_list, "doc123", store)
    assert len(candidates) == 1
    c = candidates[0]
    assert c.chunk_id == "chunk-0"
    assert c.text == "This is standard introduction text."
    assert "Google" in c.entities
    assert c.importance == 1.2
