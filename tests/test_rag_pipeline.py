import pytest
from unittest.mock import patch, MagicMock
from backend.rag_pipeline import RAGPipeline
from backend.document_graph import DocumentGraph

@patch("backend.rag_pipeline.HybridRetriever.retrieve")
@patch("backend.rag_pipeline.Reranker.rerank_candidates")
@patch("backend.rag_pipeline.get_provider")
def test_rag_pipeline_trace(mock_get_provider, mock_rerank, mock_retrieve):
    # Setup mocks
    mock_retrieve.return_value = [
        {
            "chunk_id": "chunk_1",
            "text": "Task scheduler details.",
            "sources": ["semantic"],
            "semantic_score": 0.9,
            "bm25_score": 0.0,
            "graph_score": 0.0,
            "graph_depth": 99,
            "graph_priority": 0.0,
            "chunk": {"metadata": {"type": "paragraph"}}
        }
    ]
    
    mock_rerank.return_value = mock_retrieve.return_value
    
    # Mock LLM provider
    mock_provider = MagicMock()
    mock_provider.generate.return_value = ("Synthesized answer [chunk_1].", 10, 20)
    mock_get_provider.return_value = mock_provider
    
    graph = DocumentGraph("doc_1")
    graph.add_node("chunk_1", "paragraph", 1, "Task scheduler details.")
    
    rag = RAGPipeline()
    res = rag.execute_rag("What is task scheduler?", pipeline_id=1, graph=graph)
    
    assert res["answer"] == "Synthesized answer [chunk_1]."
    assert res["intent"] == "definition"
    assert "routing" in res
    assert "retrieval" in res
    assert "reranking" in res
    assert "latency" in res
    assert len(res["citations"]) == 1
    assert res["citations"][0]["chunk_id"] == "chunk_1"
