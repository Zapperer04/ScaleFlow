import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.document_retrieval.query_understanding import QueryUnderstanding
from engine.document_retrieval.experts.vector_expert import VectorExpert
from engine.document_retrieval.experts.graph_expert import GraphExpert
from engine.document_retrieval.experts.entity_expert import EntityExpert
from engine.document_retrieval.experts.table_expert import TableExpert
from engine.document_retrieval.experts.layout_expert import LayoutExpert

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
            }
        }

    def load_json(self, doc_id, rel_path):
        return self.db.get(rel_path)

def test_vector_expert():
    store = MockStore()
    qu = QueryUnderstanding(query="test", embedding=[0.1]*768)
    exp = VectorExpert()
    results = exp.retrieve(qu, "doc123", store)
    assert len(results) > 0
    assert results[0].source == "vector"

def test_graph_expert():
    store = MockStore()
    qu = QueryUnderstanding(query="test", embedding=[0.9]*768, keywords=["introduction"])
    exp = GraphExpert()
    results = exp.retrieve(qu, "doc123", store)
    assert len(results) > 0
    assert "node-h1" in [ev.graph_node_ids[0] for ev in results]

def test_entity_expert():
    store = MockStore()
    qu = QueryUnderstanding(query="Google", entities=["Google"])
    exp = EntityExpert()
    results = exp.retrieve(qu, "doc123", store)
    assert len(results) > 0
    assert results[0].entity_ids == ["ent-1"]

def test_table_expert():
    store = MockStore()
    qu = QueryUnderstanding(query="Table", keywords=["table"], table_probability=0.9)
    exp = TableExpert()
    results = exp.retrieve(qu, "doc123", store)
    assert len(results) > 0
    assert results[0].table_ids == ["tbl-1"]

def test_layout_expert():
    store = MockStore()
    qu = QueryUnderstanding(query="bottom right", spatial_constraints=["bottom", "right"])
    exp = LayoutExpert()
    results = exp.retrieve(qu, "doc123", store)
    assert len(results) > 0
    assert results[0].layout_ids == ["node-p1"]
