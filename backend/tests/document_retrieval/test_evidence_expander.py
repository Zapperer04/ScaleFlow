import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.document_retrieval.evidence import Evidence
from services.document_retrieval.evidence_expander import EvidenceExpander

class MockStore:
    def __init__(self):
        self.db = {
            "graph/nodes.json": [
                {"id": "node-h1", "type": "Heading", "text": "Introduction"},
                {"id": "node-p1", "type": "Paragraph", "text": "This relates to Table 1"}
            ],
            "graph/edges.json": [
                {"source": "node-h1", "target": "node-p1", "type": "parent_child"}
            ]
        }
    def load_json(self, doc_id, rel_path):
        return self.db.get(rel_path)

def test_evidence_expander():
    store = MockStore()
    expander = EvidenceExpander()
    
    initial_evidence = [
        Evidence(
            id="ev-1",
            source="graph",
            evidence_type="node",
            score=0.8,
            confidence=0.9,
            graph_node_ids=["node-h1"]
        )
    ]
    
    expanded = expander.expand(initial_evidence, "doc123", store)
    assert len(expanded) == 1
    # Check that it expanded along the parent_child edge to include node-p1
    assert "node-p1" in expanded[0].graph_node_ids
