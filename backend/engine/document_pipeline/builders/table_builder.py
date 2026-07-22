from typing import Dict, Any, List
from engine.document_pipeline.builders.base_builder import BaseBuilder
from engine.document_pipeline.schemas import CanonicalDocument, TableRepresentation

class TableBuilder(BaseBuilder):
    @property
    def name(self) -> str:
        return "tables"

    @property
    def version(self) -> str:
        return "1.0.0"

    def build(self, doc: CanonicalDocument, context: Dict[str, Any]) -> List[TableRepresentation]:
        # Validate and persist table structures directly from CanonicalDocument
        tables_list: List[TableRepresentation] = []

        for table in doc.tables:
            bbox_dict = table.bbox.to_dict() if table.bbox else {"ymin": 0.0, "xmin": 0.0, "ymax": 1.0, "xmax": 1.0}
            
            # Simple validation: ensure schema rows and columns match cell limits
            max_row = max([cell.get("row", 0) for cell in table.cells], default=0) + 1
            max_col = max([cell.get("col", 0) for cell in table.cells], default=0) + 1
            
            rows = max(table.rows, max_row)
            columns = max(table.columns, max_col)

            tables_list.append(TableRepresentation(
                id=table.id,
                schema={
                    "rows": rows,
                    "columns": columns
                },
                headers=table.headers,
                cells=table.cells,
                merged_cells=table.merged_cells,
                coordinates=bbox_dict,
                page=table.page,
                caption=table.caption,
                references=table.references
            ))

        return tables_list
