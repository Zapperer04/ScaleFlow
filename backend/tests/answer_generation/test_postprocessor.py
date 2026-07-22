import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.answer_generation.answer_postprocessor import AnswerPostprocessor

def test_postprocessor_cleanup():
    processor = AnswerPostprocessor()
    
    # Check duplicate adjacent sentences
    raw_text = "This is a sentence. This is a sentence. Another unique sentence."
    processed = processor.postprocess(raw_text)
    assert processed == "This is a sentence. Another unique sentence."
    
    # Check bracket citation formatting polishing
    raw_citations = "This is verified [1] [2]."
    processed2 = processor.postprocess(raw_citations)
    assert processed2 == "This is verified [1, 2]."
