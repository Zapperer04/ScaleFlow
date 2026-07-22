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
        answer="Mock answer",
        document_id="doc123",
        sections=["Intro"],
        tables=["tbl-1"],
        query="Explain intro"
    )
    
    state = mem.get_memory(session_id)
    assert "chunk-0" in state.chunk_ids
    assert "node-p1" in state.active_graph_nodes
    assert "Google" in state.active_entities
    assert "doc123" in state.active_document_ids
    assert "Intro" in state.active_sections
    assert "tbl-1" in state.active_tables
    assert "Explain intro" in state.unresolved_questions
    assert "Mock answer" in state.previous_answers
