from typing import Dict, Any, List
from services.document_pipeline.builders.base_builder import BaseBuilder
from services.document_pipeline.schemas import CanonicalDocument, LayoutRepresentation

class LayoutBuilder(BaseBuilder):
    @property
    def name(self) -> str:
        return "layout"

    @property
    def version(self) -> str:
        return "1.0.0"

    def build(self, doc: CanonicalDocument, context: Dict[str, Any]) -> LayoutRepresentation:
        # Validate and persist layout information directly from CanonicalDocument
        raw_layout = doc.layout or {}
        
        reading_order = raw_layout.get("reading_order") or [b.id for b in doc.blocks]
        font_hierarchy = raw_layout.get("font_hierarchy", [])
        columns = raw_layout.get("columns", [])
        page_coordinates = raw_layout.get("page_coordinates", {})
        style_metadata = raw_layout.get("style_metadata", {})

        heading_level = {}
        for block in doc.blocks:
            if block.type == "heading":
                heading_level[block.id] = block.metadata.get("level", 1)

        visual_blocks = {}
        for block in doc.blocks:
            bbox_dict = block.bbox.to_dict() if block.bbox else {"ymin": 0.0, "xmin": 0.0, "ymax": 1.0, "xmax": 1.0}
            visual_blocks[block.id] = {
                "id": block.id,
                "type": block.type,
                "page": block.page,
                "bbox": bbox_dict,
                "confidence": block.confidence
            }

        return LayoutRepresentation(
            reading_order=reading_order,
            font_hierarchy=font_hierarchy,
            heading_level=heading_level,
            visual_blocks=visual_blocks,
            columns=columns,
            page_coordinates=page_coordinates,
            style_metadata=style_metadata
        )
