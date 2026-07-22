import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.document_retrieval.candidate import Candidate
from engine.answer_generation.context_formatter import ContextFormatter

def test_context_formatter_preserving():
    formatter = ContextFormatter()
    
    candidates = [
        Candidate(
            id="cand-1",
            chunk_id="chunk-0",
            source="table",
            text="Tabular data",
            score=0.9,
            confidence=0.8,
            page_numbers=[1],
            section_path=["Tables"],
            metadata={
                "table": {
                    "headers": ["A", "B"],
                    "cells": [{"row": 0, "col": 0, "text": "cell-val-1"}]
                }
            }
        )
    ]
    
    formatted = formatter.format_candidates(candidates)
    assert "cell-val-1" in formatted
    assert "Headers: A | B" in formatted
    assert "Page: 1" in formatted
