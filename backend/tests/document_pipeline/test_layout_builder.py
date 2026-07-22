import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.document_pipeline.builders.layout_builder import LayoutBuilder
from services.document_pipeline.schemas import CanonicalDocument, CanonicalBlock, BoundingBox

def test_layout_builder():
    doc = CanonicalDocument(
        document_id="testdoc123",
        blocks=[
            CanonicalBlock(id="b1", type="heading", text="Heading 1", page=1, bbox=BoundingBox(0.1, 0.1, 0.2, 0.9), metadata={"level": 2}),
            CanonicalBlock(id="b2", type="paragraph", text="Paragraph 1", page=1, bbox=BoundingBox(0.25, 0.1, 0.5, 0.9))
        ],
        layout={
            "font_hierarchy": [{"name": "Arial", "size": 12}],
            "columns": [{"index": 0, "bbox": [0,0,1,1]}]
        }
    )
    
    builder = LayoutBuilder()
    layout = builder.build(doc, {})
    
    assert layout.reading_order == ["b1", "b2"]
    assert layout.heading_level["b1"] == 2
    assert "b2" in layout.visual_blocks
    assert layout.visual_blocks["b2"]["bbox"]["ymin"] == 0.25
    assert layout.columns[0]["index"] == 0
