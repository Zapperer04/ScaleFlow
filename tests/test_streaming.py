import pytest
import json
from backend.streaming import format_sse, stream_answer_generator

def test_format_sse():
    res = format_sse("test_event", {"val": 123})
    assert res == 'event: test_event\ndata: {"val": 123}\n\n'

def test_stream_answer_generator():
    answer = "ScaleFlow is ready."
    citations = [{"file": "app.py", "range": "L1-L10"}]
    trace_id = "tr-12345"
    
    generator = stream_answer_generator(answer, citations, trace_id, delay=0.0)
    events = list(generator)
    
    assert len(events) == 5  # "ScaleFlow", "is", "ready.", citation event, complete event
    
    # Check first delta event
    assert "event: delta" in events[0]
    first_data = json.loads(events[0].split("data: ")[1].split("\n\n")[0])
    assert first_data["text"] == "ScaleFlow "
    assert first_data["trace_id"] == "tr-12345"
    
    # Check citation event
    assert "event: citation" in events[3]
    cit_data = json.loads(events[3].split("data: ")[1].split("\n\n")[0])
    assert cit_data["citation"] == citations[0]
    
    # Check complete event
    assert "event: complete" in events[4]
    complete_data = json.loads(events[4].split("data: ")[1].split("\n\n")[0])
    assert complete_data["done"] is True
