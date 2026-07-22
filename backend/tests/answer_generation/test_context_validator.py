import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.document_retrieval.candidate import Candidate
from services.answer_generation.context_validator import ContextValidator

def test_context_validator_dedup_and_contradiction():
    validator = ContextValidator()
    
    candidates = [
        Candidate(
            id="cand-1",
            chunk_id="chunk-0",
            source="vector",
            text="The project cost is $500000.",
            score=0.9,
            confidence=0.8
        ),
        # Duplicate text
        Candidate(
            id="cand-2",
            chunk_id="chunk-1",
            source="vector",
            text="The project cost is $500000.",
            score=0.8,
            confidence=0.8
        ),
        # Contradictory text (different amount)
        Candidate(
            id="cand-3",
            chunk_id="chunk-2",
            source="vector",
            text="The project cost is $900000.",
            score=0.85,
            confidence=0.8
        )
    ]
    
    validated = validator.validate_context(candidates)
    
    # Should deduplicate exact match -> leaving 2 candidates
    assert len(validated) == 2
    
    # Check that contradiction warning was recorded
    assert "contradictory_warnings" in validated[0].metadata
    assert len(validated[0].metadata["contradictory_warnings"]) > 0
