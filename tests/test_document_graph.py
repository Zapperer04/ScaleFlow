import pytest
from backend.document_graph import DocumentGraph

def test_document_graph_creation_and_versioning():
    graph = DocumentGraph(document_id="doc_123", version=1, schema="document-graph-v1")
    
    assert graph.document_id == "doc_123"
    assert graph.version == 1
    assert graph.schema == "document-graph-v1"

def test_add_page_and_node():
    graph = DocumentGraph(document_id="doc_123")
    
    # Page
    page = graph.add_page(page_number=1, width=100.0, height=200.0)
    assert page["page_number"] == 1
    assert len(graph.pages) == 1

    # Node
    node = graph.add_node(
        node_id="sec_1",
        node_type="section",
        page=1,
        text="Introduction Section",
        bbox={"ymin": 0.0, "xmin": 0.0, "ymax": 0.5, "xmax": 1.0}
    )
    
    assert node["id"] == "sec_1"
    assert node["type"] == "section"
    assert node["text"] == "Introduction Section"
    assert graph.get_node("sec_1") == node

def test_add_edge_and_lookup():
    graph = DocumentGraph(document_id="doc_123")
    
    graph.add_node("n1", "paragraph", 1, "First paragraph")
    graph.add_node("n2", "paragraph", 1, "Second paragraph")
    
    # Edge
    edge = graph.add_edge(source="n1", target="n2", edge_type="next")
    assert edge["source"] == "n1"
    assert edge["target"] == "n2"
    assert edge["type"] == "next"

    outbound = graph.get_outbound_edges("n1")
    assert len(outbound) == 1
    assert outbound[0]["target"] == "n2"

    inbound = graph.get_inbound_edges("n2")
    assert len(inbound) == 1
    assert inbound[0]["source"] == "n1"

def test_serialization():
    graph = DocumentGraph(document_id="doc_abc")
    graph.add_page(1, 500, 600)
    graph.add_node("n1", "paragraph", 1, "Hello")
    graph.add_node("n2", "paragraph", 1, "World", parent="n1")
    graph.add_edge("n1", "n2", "contains")

    data = graph.to_dict()
    assert data["version"] == 1
    assert data["schema"] == "document-graph-v1"
    assert len(data["nodes"]) == 2
    assert len(data["edges"]) == 1

    # Deserialize
    recreated = DocumentGraph.from_dict(data)
    assert recreated.document_id == "doc_abc"
    assert len(recreated.nodes) == 2
    assert len(recreated.edges) == 1
    assert recreated.get_node("n2")["parent"] == "n1"
