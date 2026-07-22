import os
import sys
import pytest
import hashlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.document_pipeline.builders.graph_builder import GraphBuilder
from engine.document_pipeline.schemas import CanonicalDocument, CanonicalBlock, CanonicalTable, BoundingBox

def test_graph_builder_rich_structure():
    doc_id = "testdoc123"
    doc_node_id = f"doc-{hashlib.sha256(doc_id.encode()).hexdigest()[:16]}"
    
    # Simulating VLM parsed graph
    raw_graph = {
        "nodes": [
            {"id": doc_node_id, "type": "Document", "text": "testdoc123", "page": 1},
            {"id": "node-h1", "type": "Heading", "text": "Introduction", "page": 1},
            {"id": "node-p1", "type": "Paragraph", "text": "This is standard text referring to table 1", "page": 1},
            {"id": "node-c1", "type": "Caption", "text": "Table 1 Caption", "page": 1},
            {"id": "node-tbl1", "type": "Table", "text": "Table: Table 1", "page": 1}
        ],
        "edges": [
            {"source": doc_node_id, "target": "node-h1", "type": "contains"},
            {"source": doc_node_id, "target": "node-p1", "type": "contains"},
            {"source": doc_node_id, "target": "node-c1", "type": "contains"},
            {"source": doc_node_id, "target": "node-tbl1", "type": "contains"},
            {"source": "node-h1", "target": "node-p1", "type": "parent_child"},
            {"source": "node-p1", "target": "node-c1", "type": "next"},
            {"source": "node-c1", "target": "node-p1", "type": "previous"},
            {"source": "node-p1", "target": "node-tbl1", "type": "references"},
            {"source": "node-c1", "target": "node-tbl1", "type": "caption_of"}
        ]
    }

    doc = CanonicalDocument(
        document_id=doc_id,
        blocks=[
            CanonicalBlock(id="h1", type="heading", text="Introduction", page=1, bbox=BoundingBox(0,0,1,1)),
            CanonicalBlock(id="p1", type="paragraph", text="This is standard text referring to table 1", page=1),
            CanonicalBlock(id="c1", type="caption", text="Table 1 Caption", page=1)
        ],
        tables=[
            CanonicalTable(id="tbl1", page=1, rows=2, columns=2, caption="Table 1")
        ],
        graph=raw_graph
    )
    
    builder = GraphBuilder()
    context = {}
    graph = builder.build(doc, context)
    
    nodes = {n["id"]: n for n in graph["nodes"]}
    edges = graph["edges"]
    
    # Check node types
    assert doc_node_id in nodes
    assert nodes["node-h1"]["type"] == "Heading"
    assert nodes["node-p1"]["type"] == "Paragraph"
    assert nodes["node-c1"]["type"] == "Caption"
    assert nodes["node-tbl1"]["type"] == "Table"
    
    # Check parent_child edge
    parent_child_edges = [e for e in edges if e["type"] == "parent_child"]
    assert len(parent_child_edges) > 0
    
    # Check next / previous edge
    next_edges = [e for e in edges if e["type"] == "next"]
    assert len(next_edges) == 1
    
    # Check references (p1 refers to tbl1)
    ref_edges = [e for e in edges if e["type"] == "references" and e["source"] == "node-p1" and e["target"] == "node-tbl1"]
    assert len(ref_edges) == 1
    
    # Check caption_of (c1 caption_of tbl1)
    caption_edges = [e for e in edges if e["type"] == "caption_of" and e["source"] == "node-c1" and e["target"] == "node-tbl1"]
    assert len(caption_edges) == 1
