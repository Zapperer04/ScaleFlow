import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.document_pipeline.builders.chunk_builder import ChunkBuilder
from services.document_pipeline.schemas import CanonicalDocument, CanonicalBlock, BoundingBox

def test_chunk_builder_semantic_logic():
    doc = CanonicalDocument(
        document_id="testdoc123",
        blocks=[
            CanonicalBlock(id="h1", type="heading", text="Chapter One", page=1, bbox=BoundingBox(0.1, 0.1, 0.2, 0.9)),
            CanonicalBlock(id="p1", type="paragraph", text="This is standard body text containing the term Company LLC. We can reference Table 1 here.", page=1, bbox=BoundingBox(0.2, 0.1, 0.4, 0.9)),
            CanonicalBlock(id="h2", type="heading", text="Chapter Two", page=1, bbox=BoundingBox(0.4, 0.1, 0.5, 0.9)),
            CanonicalBlock(id="p2", type="paragraph", text="This is the second section text. Mentioning Person Name.", page=1)
        ],
        sections=[
            {"heading_id": "h1", "title": "Chapter One"},
            {"heading_id": "h2", "title": "Chapter Two"}
        ]
    )
    
    # Mock entities output
    class MockEntity:
        def __init__(self, name):
            self.name = name
            
    class MockEntityGraph:
        def __init__(self):
            self.entities = [MockEntity("Company LLC"), MockEntity("Person Name")]

    context = {"entities": MockEntityGraph()}
    
    builder = ChunkBuilder()
    chunks = builder.build(doc, context)
    
    # Expecting 2 chunks split at headings
    assert len(chunks) == 2
    
    # Check chunk 0
    c0 = chunks[0]
    assert c0.chunk_id == "chunk-0"
    assert c0.parent_node == "h1"
    assert c0.section_path == ["Chapter One"]
    assert "Company LLC" in c0.entities
    assert "Table 1" in c0.table_refs
    assert c0.summary is not None
    assert c0.importance_score > 1.0
    assert c0.next_chunk == "chunk-1"
    
    # Check chunk 1
    c1 = chunks[1]
    assert c1.chunk_id == "chunk-1"
    assert c1.parent_node == "h2"
    assert c1.previous_chunk == "chunk-0"
    assert "Person Name" in c1.entities
