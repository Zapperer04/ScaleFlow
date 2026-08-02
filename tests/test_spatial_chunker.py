import pytest
from backend.spatial_chunker import SpatialChunker

def test_spatial_chunker_rules():
    chunker = SpatialChunker(max_tokens=20)
    
    # Mock document graph dict
    graph = {
        "document_id": "test_doc",
        "pages": [{"page_number": 1, "width": 100, "height": 100}],
        "nodes": [
            {"id": "n1", "type": "heading", "page": 1, "text": "Section Heading", "reading_order": 1},
            {"id": "n2", "type": "paragraph", "page": 1, "text": "This is paragraph one with several words.", "reading_order": 2},
            {"id": "n3", "type": "paragraph", "page": 1, "text": "This is paragraph two.", "reading_order": 3},
            {"id": "n4", "type": "table", "page": 1, "text": "| header | cell |", "reading_order": 4}
        ],
        "edges": []
    }

    chunks = chunker.chunk_document(graph)
    
    # Heading chunk, merged paragraphs chunk, table chunk
    assert len(chunks) == 3
    assert chunks[0]["heading"] == "Section Heading"
    assert chunks[0]["graph_node_ids"] == ["n1"]
    
    # Paragraphs n2 and n3 merged since they fit within token limit
    assert chunks[1]["graph_node_ids"] == ["n2", "n3"]
    
    # Table must not be split or merged
    assert chunks[2]["graph_node_ids"] == ["n4"]
    assert chunks[2]["section_id"] == "n1" # inherits active section
