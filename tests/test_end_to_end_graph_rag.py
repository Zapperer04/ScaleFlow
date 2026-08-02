import pytest
import os
from unittest.mock import patch, MagicMock

@patch("ingestion_pipeline.parse_pdf")
@patch("ingestion_pipeline.embed_text")
@patch("ingestion_pipeline.upsert_document_chunks")
@patch("ingestion_pipeline.rebuild_bm25_index")
@patch("rag_pipeline.get_provider")
@patch("hybrid_retriever.embed_text")
@patch("hybrid_retriever.search_similar")
@patch("hybrid_retriever.retrieve_bm25")
def test_end_to_end_graph_rag_pipeline(
    mock_retrieve_bm25,
    mock_search_similar,
    mock_hybrid_embed,
    mock_get_provider,
    mock_rebuild_bm25,
    mock_upsert,
    mock_embed,
    mock_parse_pdf
):
    # Import locally within the test to ensure patches are applied before module loading
    from ingestion_pipeline import IngestionPipeline
    from rag_pipeline import RAGPipeline
    from document_graph import DocumentGraph

    # Setup Ingestion Mocks
    mock_parse_result = MagicMock()
    mock_parse_result.document_graph = {
        "pages": [{
            "page_number": 1,
            "width": 600,
            "height": 800,
            "nodes": [
                {"id": "node_1", "structural_type": "heading", "text": "ScaleFlow Overview", "reading_order": 1},
                {"id": "node_2", "structural_type": "paragraph", "text": "ScaleFlow is a high-availability task manager.", "reading_order": 2}
            ],
            "edges": []
        }]
    }
    mock_parse_pdf.return_value = mock_parse_result
    mock_embed.return_value = [0.1] * 384
    mock_hybrid_embed.return_value = [0.1] * 384
    mock_upsert.return_value = (True, 0.05, 0.05, 2)
    
    pipeline = IngestionPipeline()
    graph_dict, chunks = pipeline.run_ingestion("dummy.pdf", pipeline_id=99, file_id=1, task_id=101)
    
    assert len(chunks) == 2
    assert chunks[0]["heading"] == "ScaleFlow Overview"
    assert chunks[1]["text"] == "ScaleFlow is a high-availability task manager."

    # Setup RAG Mocks
    mock_similar_pt = MagicMock()
    mock_similar_pt.score = 0.95
    mock_similar_pt.payload = {
        "chunk_id": "chunk_99_2",
        "chunk_text": "ScaleFlow is a high-availability task manager.",
        "page": 1,
        "graph_node_ids": ["node_2"]
    }
    mock_search_similar.return_value = [mock_similar_pt]
    mock_retrieve_bm25.return_value = []
    
    mock_provider = MagicMock()
    mock_provider.generate.return_value = ("ScaleFlow operates as a high-availability task manager [chunk_99_2].", 15, 30)
    mock_get_provider.return_value = mock_provider

    # Build graph object manually matching ingestion graph dict
    graph = DocumentGraph.from_dict(graph_dict)

    rag = RAGPipeline()
    result = rag.execute_rag("What is ScaleFlow?", pipeline_id=99, graph=graph)

    # Validate end-to-end RAG answer and citation
    assert result["answer"] == "ScaleFlow operates as a high-availability task manager [chunk_99_2]."
    assert len(result["citations"]) == 1
    assert result["citations"][0]["chunk_id"] == "chunk_99_2"
    assert result["citations"][0]["page"] == 1
    assert result["citations"][0]["graph_node_id"] == "node_2"
