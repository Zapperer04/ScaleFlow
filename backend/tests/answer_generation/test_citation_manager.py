import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.document_retrieval.candidate import Candidate
from engine.answer_generation.citation_manager import CitationManager

def test_citation_parsing():
    manager = CitationManager()
    
    candidates = [
        Candidate(
            id="cand-1",
            chunk_id="chunk-0",
            source="vector",
            text="First chunk content",
            score=0.9,
            confidence=0.8,
            page_numbers=[1]
        ),
        Candidate(
            id="cand-2",
            chunk_id="chunk-1",
            source="graph",
            text="Second chunk content",
            score=0.85,
            confidence=0.8,
            page_numbers=[2]
        )
    ]
    
    answer = "Based on [1], the first part holds, and according to [2], the second follows."
    citations = manager.parse_citations(answer, candidates)
    
    assert len(citations) == 2
    assert citations[0].chunk_id == "chunk-0"
    assert citations[1].chunk_id == "chunk-1"
    assert citations[0].page_numbers == [1]
