import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.document_retrieval.candidate import Candidate
from services.document_retrieval.query_understanding import QueryUnderstanding
from services.answer_generation.prompt_builder import PromptBuilder

def test_prompt_builder_formatting():
    builder = PromptBuilder()
    
    candidates = [
        Candidate(
            id="cand-1",
            chunk_id="chunk-0",
            source="vector",
            text="This is standard introduction text.",
            score=0.9,
            confidence=0.8,
            page_numbers=[1],
            section_path=["Introduction"]
        )
    ]
    
    qu = QueryUnderstanding(query="What is the introduction?", table_probability=0.1)
    prompt = builder.build_prompt("What is the introduction?", qu, candidates)
    
    assert "What is the introduction?" in prompt
    assert "This is standard introduction text." in prompt
    assert "Introduction" in prompt
