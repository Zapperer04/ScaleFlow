import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.document_pipeline.builders.entity_builder import EntityBuilder
from engine.document_pipeline.schemas import CanonicalDocument, CanonicalBlock, CanonicalEntity

def test_entity_builder_extraction():
    # In simplified design, entities are returned directly by VLM parser, not extracted in Python
    doc = CanonicalDocument(
        document_id="testdoc123",
        blocks=[
            CanonicalBlock(id="b1", type="paragraph", text="The Google Corp was founded in Jan 1, 1998.", page=1)
        ],
        entities=[
            CanonicalEntity(
                name="Google",
                type="Organization",
                normalized_value="Google",
                aliases=["Google Corp"],
                occurrences=[{"page": 1, "block_id": "b1"}]
            )
        ]
    )
    
    builder = EntityBuilder()
    entity_graph = builder.build(doc, {})
    
    entities = {e.normalized_value.lower(): e for e in entity_graph.entities}
    
    assert "google" in entities
    assert entities["google"].type == "Organization"
    assert "Google Corp" in entities["google"].aliases

    # Verify relation edges
    appears_in_edges = [edge for edge in entity_graph.edges if edge.type == "appears_in"]
    assert len(appears_in_edges) > 0
