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

def test_orchestrator_self_reflection(monkeypatch):
    monkeypatch.setenv("TEST_OFFLINE_MODE", "True")
    orchestrator = AnswerOrchestrator()
    
    # Setup candidates with specific text
    candidates = [
        Candidate(
            id="cand-1",
            chunk_id="chunk-0",
            source="vector",
            text="The project cost is $500000.",
            score=0.9,
            confidence=0.8
        )
    ]
    
    # Mock generator to return invalid/unsupported text first, then valid text upon retry
    call_count = 0
    def mock_generate_answer(prompt):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Contains unsupported claim about Microsoft and no citations
            return {
                "text": "The project cost was funded by Microsoft.",
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "provider": "mock",
                "model": "mock-reflection"
            }
        else:
            # Contains correct citation and valid claim
            return {
                "text": "The project cost is $500000 [1].",
                "prompt_tokens": 120,
                "completion_tokens": 80,
                "provider": "mock",
                "model": "mock-reflection"
            }
            
    orchestrator.generator.generate_answer = mock_generate_answer
    
    qu = QueryUnderstanding(query="How much did the project cost?", table_probability=0.1)
    
    # Run Orchestrator with max_retries = 1
    result = orchestrator.generate_answer(
        query="How much did the project cost?",
        qu=qu,
        candidates=candidates,
        retrieval_confidence=0.8,
        max_retries=1
    )
    
    # Verify E2E Self-Reflection execution
    assert call_count == 2
    assert result.verification.is_valid
    assert "500000" in result.text
    assert result.metrics.retry_count == 1
