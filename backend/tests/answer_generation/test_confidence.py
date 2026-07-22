import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.document_retrieval.candidate import Candidate
from engine.answer_generation.verifier import VerificationResult
from engine.answer_generation.confidence import ConfidenceEngine

def test_confidence_calculations():
    engine = ConfidenceEngine()
    
    candidates = [
        Candidate(
            id="cand-1",
            chunk_id="chunk-0",
            source="vector",
            text="Context info",
            score=0.9,
            confidence=0.8
        )
    ]
    
    v_result = VerificationResult(is_valid=True, verification_score=0.95)
    
    conf = engine.calculate_confidence(
        retrieval_confidence=0.9,
        verification=v_result,
        candidates=candidates,
        answer_text="Here is the answer citing context [1]."
    )
    
    assert conf.overall_score > 0.6
    assert conf.confidence_breakdown["retrieval"] == 0.9
    assert conf.confidence_breakdown["verification"] == 0.95
