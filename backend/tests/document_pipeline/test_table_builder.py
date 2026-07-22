import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.document_pipeline.builders.table_builder import TableBuilder
from engine.document_pipeline.schemas import CanonicalDocument, CanonicalTable, BoundingBox

def test_table_builder():
    doc = CanonicalDocument(
        document_id="testdoc123",
        tables=[
            CanonicalTable(
                id="t1",
                page=2,
                rows=3,
                columns=4,
                headers=["Col1", "Col2", "Col3", "Col4"],
                cells=[{"row": 0, "col": 0, "text": "value"}],
                merged_cells=[{"row_start": 0, "row_end": 1, "col_start": 0, "col_end": 0}],
                bbox=BoundingBox(0.1, 0.1, 0.5, 0.8),
                caption="Data Table",
                references=["section-1"]
            )
        ]
    )
    
    builder = TableBuilder()
    tables = builder.build(doc, {})
    
    assert len(tables) == 1
    t = tables[0]
    assert t.id == "t1"
    assert t.schema == {"rows": 3, "columns": 4}
    assert t.headers == ["Col1", "Col2", "Col3", "Col4"]
    assert t.cells[0]["text"] == "value"
    assert t.merged_cells[0]["row_start"] == 0
    assert t.caption == "Data Table"
    assert t.references == ["section-1"]
