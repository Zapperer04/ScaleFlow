import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.document_retrieval.candidate import Candidate
from engine.document_retrieval.context_optimizer import ContextOptimizer

def test_context_optimizer():
    optimizer = ContextOptimizer()
    
    candidates = [
        # Adjacent chunks in document index order (chunk-0 and chunk-1)
        Candidate(
            id="cand-1",
            chunk_id="chunk-0",
            source="vector",
            text="First sentence.",
            score=0.9,
            confidence=0.8
        ),
        Candidate(
            id="cand-2",
            chunk_id="chunk-1",
            source="vector",
            text="Second sentence.",
            score=0.8,
            confidence=0.8
        )
    ]
    
    optimized = optimizer.optimize_context(candidates, token_limit=100)
    # They should be stitched together because they are sequential neighbors
    assert len(optimized) == 1
    assert optimized[0].text == "First sentence.\nSecond sentence."
