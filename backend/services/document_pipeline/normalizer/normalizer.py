import hashlib
from typing import Dict, Any, List
from services.document_pipeline.schemas import (
    CanonicalDocument,
    CanonicalBlock,
    CanonicalTable,
    CanonicalEntity,
    BoundingBox
)

class CanonicalNormalizer:
    def normalize(self, raw_output: Dict[str, Any]) -> CanonicalDocument:
        filepath = raw_output.get("document_path", "")
        document_id = hashlib.sha256(filepath.encode()).hexdigest()

        # Parse Canonical blocks
        blocks = []
        for b in raw_output.get("blocks", []):
            bbox_raw = b.get("bbox")
            bbox = None
            if bbox_raw:
                if isinstance(bbox_raw, dict):
                    bbox = BoundingBox(
                        ymin=float(bbox_raw.get("ymin", 0.0)),
                        xmin=float(bbox_raw.get("xmin", 0.0)),
                        ymax=float(bbox_raw.get("ymax", 1.0)),
                        xmax=float(bbox_raw.get("xmax", 1.0))
                    )
                elif isinstance(bbox_raw, (list, tuple)) and len(bbox_raw) >= 4:
                    bbox = BoundingBox(
                        ymin=float(bbox_raw[1]),
                        xmin=float(bbox_raw[0]),
                        ymax=float(bbox_raw[3]),
                        xmax=float(bbox_raw[2])
                    )
            blocks.append(CanonicalBlock(
                id=b.get("id"),
                type=b.get("type", "paragraph"),
                text=b.get("text", ""),
                page=b.get("page", 1),
                bbox=bbox,
                confidence=float(b.get("confidence", 1.0)),
                metadata=b.get("metadata", {})
            ))

        # Parse Canonical tables
        tables = []
        for t in raw_output.get("tables", []):
            bbox_raw = t.get("bbox")
            bbox = None
            if bbox_raw:
                if isinstance(bbox_raw, dict):
                    bbox = BoundingBox(
                        ymin=float(bbox_raw.get("ymin", 0.0)),
                        xmin=float(bbox_raw.get("xmin", 0.0)),
                        ymax=float(bbox_raw.get("ymax", 1.0)),
                        xmax=float(bbox_raw.get("xmax", 1.0))
                    )
                elif isinstance(bbox_raw, (list, tuple)) and len(bbox_raw) >= 4:
                    bbox = BoundingBox(
                        ymin=float(bbox_raw[1]),
                        xmin=float(bbox_raw[0]),
                        ymax=float(bbox_raw[3]),
                        xmax=float(bbox_raw[2])
                    )
            tables.append(CanonicalTable(
                id=t.get("id"),
                page=t.get("page", 1),
                rows=t.get("rows", 0),
                columns=t.get("columns", 0),
                headers=t.get("headers", []),
                cells=t.get("cells", []),
                merged_cells=t.get("merged_cells", []),
                bbox=bbox,
                caption=t.get("caption"),
                references=t.get("references", [])
            ))

        # Parse Canonical entities
        entities = []
        for e in raw_output.get("entities", []):
            entities.append(CanonicalEntity(
                name=e.get("name", ""),
                type=e.get("type", "Domain Entity"),
                normalized_value=e.get("normalized_value", e.get("name", "")),
                aliases=e.get("aliases", []),
                occurrences=e.get("occurrences", [])
            ))

        metadata = raw_output.get("metadata", {})
        layout = raw_output.get("layout", {})
        graph = raw_output.get("graph", {})
        sections = raw_output.get("sections", [])
        figures = raw_output.get("figures", [])
        document_info = raw_output.get("document", {})

        parser_metadata = {
            "parser_used": raw_output.get("parser_used", "unknown"),
            "timings": raw_output.get("timings", {}),
            "vlm": raw_output.get("vlm_metadata", {})
        }

        return CanonicalDocument(
            document_id=document_id,
            document=document_info,
            pages=raw_output.get("pages", []),
            blocks=blocks,
            sections=sections,
            graph=graph,
            entities=entities,
            tables=tables,
            figures=figures,
            layout=layout,
            metadata=metadata,
            parser_metadata=parser_metadata
        )
