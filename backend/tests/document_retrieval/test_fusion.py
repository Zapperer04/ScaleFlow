import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.document_retrieval.candidate import Candidate
from services.document_retrieval.query_understanding import QueryUnderstanding
from services.document_retrieval.fusion import FusionEngine

def test_fusion_and_agreement_boost():
    engine = FusionEngine()
    
    # Simulating same chunk retrieved by two different experts (vector and graph)
    candidates = [
        Candidate(
            id="cand-1",
            chunk_id="chunk-0",
            source="vector",
            text="hello world",
            score=0.7,
            confidence=0.8
        ),
        Candidate(
            id="cand-2",
            chunk_id="chunk-0",
            source="graph",
            text="hello world",
            score=0.6,
            confidence=0.9
        )
    ]
    
    qu = QueryUnderstanding(query="hello", table_probability=0.1)
    fused = engine.fuse_candidates(candidates, qu)
    
    # Should fuse into 1 unique chunk candidate
    assert len(fused) == 1
    
    fused_c = fused[0]
    # Check that score has received an agreement boost (> 0.7 + avg_confidence*0.2)
    assert fused_c.score > 0.8
    assert len(fused_c.metadata["confidence_breakdown"]["sources"]) == 2
