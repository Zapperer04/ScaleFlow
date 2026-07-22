import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.document_pipeline.normalizer.normalizer import CanonicalNormalizer
from services.document_pipeline.schemas import CanonicalDocument

def test_canonical_normalizer_conversion():
    raw_data = {
        "document_path": "dummy.pdf",
        "parser_used": "test_parser",
        "pages": [
            {
                "page": 1,
                "text": "Hello world"
            }
        ],
        "blocks": [
            {
                "id": "b1",
                "type": "heading",
                "text": "Hello world",
                "page": 1,
                "bbox": [0.1, 0.1, 0.9, 0.9],
                "confidence": 0.95
            }
        ],
        "tables": [
            {
                "id": "t1",
                "page": 1,
                "rows": 2,
                "columns": 2,
                "headers": ["A", "B"],
                "cells": [{"row": 0, "col": 0, "text": "cell1"}],
                "caption": "Test Table"
            }
        ]
    }
    
    normalizer = CanonicalNormalizer()
    doc = normalizer.normalize(raw_data)
    
    assert isinstance(doc, CanonicalDocument)
    assert doc.document_id is not None
    assert len(doc.blocks) == 1
    assert doc.blocks[0].type == "heading"
    assert doc.blocks[0].confidence == 0.95
    assert len(doc.tables) == 1
    assert doc.tables[0].caption == "Test Table"
