import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.document_pipeline.builders.embedding_builder import EmbeddingBuilder
from services.document_pipeline.schemas import CanonicalDocument, SemanticChunk, CanonicalBlock, TableRepresentation, EntityGraph, EntityRecord

def test_embedding_builder_multi_level():
    # Setup mock representations
    chunks = [
        SemanticChunk(
            chunk_id="chunk-0",
            text="This is simple body text for chunk zero.",
            summary="summary",
            parent_node="h1",
            section_path=["Section"],
            page_range=[1],
            bbox={"ymin": 0.0, "xmin": 0.0, "ymax": 1.0, "xmax": 1.0},
            entities=["Google"],
            graph_node_ids=["b1"]
        )
    ]
    
    # We pass these through context
    class MockEntityGraph:
        def __init__(self):
            self.entities = [EntityRecord(id="ent-0", name="Google", type="Organization", normalized_value="Google")]
            
    context = {
        "chunks": chunks,
        "entities": MockEntityGraph(),
        "tables": [TableRepresentation(id="t1", page=1, caption="Revenue in 2026")]
    }
    
    doc = CanonicalDocument(
        document_id="doc123",
        blocks=[CanonicalBlock(id="h1", type="heading", text="Main Heading", page=1)]
    )
    
    builder = EmbeddingBuilder()
    embeddings = builder.build(doc, context)
    
    # Check types and counts
    types = [e.metadata["type"] for e in embeddings]
    assert "chunk" in types
    assert "heading" in types
    assert "entity" in types
    assert "table_summary" in types
    
    # Dimension validation
    for emb in embeddings:
        assert len(emb.vector) == 768
        assert emb.embedding_model is not None
        assert emb.embedding_version == "1.0.0"
