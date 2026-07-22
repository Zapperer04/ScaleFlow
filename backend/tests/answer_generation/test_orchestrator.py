import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.document_retrieval.candidate import Candidate
from services.document_retrieval.query_understanding import QueryUnderstanding
from services.answer_generation.orchestrator import AnswerOrchestrator

def test_orchestrator_e2e_answer_generation(monkeypatch):
    monkeypatch.setenv("TEST_OFFLINE_MODE", "True")
    orchestrator = AnswerOrchestrator()
    
    candidates = [
        Candidate(
            id="cand-1",
            chunk_id="chunk-0",
            source="vector",
            text="Google Corp was founded in Jan 1, 1998.",
            score=0.9,
            confidence=0.8,
            page_numbers=[1]
        )
    ]
    
    qu = QueryUnderstanding(query="When was Google Corp founded?", table_probability=0.1)
    
    # E2E Orchestrated Generation
    result = orchestrator.generate_answer(
        query="When was Google Corp founded?",
        qu=qu,
        candidates=candidates,
        retrieval_confidence=0.8
    )
    
    assert result.text is not None
    assert len(result.citations) > 0
    assert result.citations[0].chunk_id == "chunk-0"
    assert result.metrics.prompt_tokens > 0
    assert result.confidence.overall_score > 0.5
