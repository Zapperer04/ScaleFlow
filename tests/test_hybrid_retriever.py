import pytest
from unittest.mock import patch, MagicMock
from backend.hybrid_retriever import HybridRetriever
from backend.document_graph import DocumentGraph

@patch("backend.hybrid_retriever.embed_text")
@patch("backend.hybrid_retriever.search_similar")
@patch("backend.hybrid_retriever.retrieve_bm25")
def test_hybrid_retriever_merge(mock_bm25, mock_similar, mock_embed):
    # Setup mocks
    mock_embed.return_value = [0.1] * 384
    
    mock_similar_point = MagicMock()
    mock_similar_point.score = 0.92
    mock_similar_point.payload = {
        "chunk_id": "chunk_1",
        "chunk_text": "Semantic match text",
        "graph_node_ids": ["n1"]
    }
    mock_similar.return_value = [mock_similar_point]
    
    mock_bm25.return_value = [{
        "chunk_id": "chunk_1",
        "chunk_text": "Semantic match text",
        "score": 4.5,
        "graph_node_ids": ["n1"]
    }, {
        "chunk_id": "chunk_2",
        "chunk_text": "Lexical match text",
        "score": 6.1,
        "graph_node_ids": ["n2"]
    }]
    
    graph = DocumentGraph("doc_test")
    graph.add_node("n1", "paragraph", 1, "Semantic match text")
    graph.add_node("n2", "paragraph", 1, "Lexical match text")

    retriever = HybridRetriever(traversal_depth=0)
    results = retriever.retrieve("match", pipeline_id=1, top_k=5, graph=graph)

    # Validate merging and sources mapping
    assert len(results) == 2
    
    c1 = next(r for r in results if r["chunk_id"] == "chunk_1")
    assert "semantic" in c1["sources"]
    assert "bm25" in c1["sources"]
    assert c1["semantic_score"] == 0.92
    assert c1["bm25_score"] == 4.5

    c2 = next(r for r in results if r["chunk_id"] == "chunk_2")
    assert "bm25" in c2["sources"]
