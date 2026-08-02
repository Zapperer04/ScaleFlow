import pytest
from backend.document_graph import DocumentGraph
from backend.graph_retriever import GraphRetriever

def test_graph_retriever_traversal():
    graph = DocumentGraph("doc_test")
    graph.add_page(1, 100, 100)
    graph.add_node("n1", "section", 1, "Section 1")
    graph.add_node("n2", "paragraph", 1, "Paragraph 1", parent="n1")
    graph.add_node("n3", "table", 1, "| table |", parent="n1")
    graph.add_edge("n2", "n3", "references")
    
    retriever = GraphRetriever(traversal_depth=1)
    
    # Retrieve starting from n2
    res = retriever.retrieve(graph, query="", start_node_ids=["n2"])
    
    node_ids = [n["id"] for n in res.nodes]
    # Should find n2, parent n1, referent n3, and sibling n3
    assert "n2" in node_ids
    assert "n1" in node_ids
    assert "n3" in node_ids
