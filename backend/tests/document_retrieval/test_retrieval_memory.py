import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.document_retrieval.retrieval_memory import RetrievalSessionMemory

def test_session_memory_flow():
    mem = RetrievalSessionMemory()
    session_id = "session-999"
    
    mem.add_turn(
        session_id=session_id,
        chunk_ids=["chunk-0"],
        node_ids=["node-p1"],
        entity_ids=["Google"],
        answer="Mock answer"
    )
    
    state = mem.get_memory(session_id)
    assert "chunk-0" in state["chunk_ids"]
    assert "node-p1" in state["node_ids"]
    assert "Google" in state["entity_ids"]
