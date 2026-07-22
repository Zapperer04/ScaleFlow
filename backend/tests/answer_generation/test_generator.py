import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.answer_generation.answer_generator import AnswerGenerator

def test_answer_generator_fallback(monkeypatch):
    monkeypatch.setenv("TEST_OFFLINE_MODE", "True")
    generator = AnswerGenerator()
    res = generator.generate_answer("Who is the founder of Google?")
    
    assert "text" in res
    assert "Google Corp" in res["text"]
    assert "[1]" in res["text"]
