import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.document_retrieval.candidate import Candidate
from engine.answer_generation.verifier import AnswerVerifier

def test_verifier_catches_unsupported():
    verifier = AnswerVerifier()
    
    candidates = [
        Candidate(
            id="cand-1",
            chunk_id="chunk-0",
            source="vector",
            text="The project was funded by Zapperer.",
            score=0.9,
            confidence=0.8
        )
    ]
    
    # Valid answer (Google Corp is matched in test as Zapperer has Zapperer)
    valid_text = "The funding came from Zapperer [1]."
    v_res = verifier.verify(valid_text, candidates)
    assert v_res.is_valid
    
    # Unsupported claim (claims about Microsoft)
    unsupported_text = "The funding came from Microsoft [1]."
    v_res2 = verifier.verify(unsupported_text, candidates)
    assert len(v_res2.unsupported_claims) > 0
    assert not v_res2.is_valid
