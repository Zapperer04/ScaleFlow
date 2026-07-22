import sys
import os
import pytest
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from backend.platform.storage.conversation_store import ConversationStore
from backend.platform.services.conversation_service import ConversationService
from engine.document_retrieval.retrieval_memory import RetrievalSessionMemory

@pytest.fixture
def temp_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    # Create tables
    cursor.execute("""
    CREATE TABLE conversations (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("""
    CREATE TABLE conversation_state (
        conversation_id TEXT PRIMARY KEY,
        state_json TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("""
    CREATE TABLE conversation_turns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT NOT NULL,
        user_message TEXT NOT NULL,
        assistant_message TEXT NOT NULL,
        citations_json TEXT,
        metrics_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    yield conn
    conn.close()

def test_conversation_history_and_state_recovery(temp_db):
    store = ConversationStore(temp_db)
    service = ConversationService(store)
    
    conv_id = service.start_conversation("first query")
    
    # Verify title
    conv = store.get_conversation(conv_id)
    assert conv["title"] == "first query"
    
    # Persist mock session state
    session_memory = RetrievalSessionMemory()
    state = session_memory.get_memory(conv_id)
    state.active_document_ids = ["doc_123"]
    state.chunk_ids = ["c1", "c2"]
    
    service.persist_session_state(conv_id, session_memory)
    
    # Recover session state in new memory instance
    new_session_memory = RetrievalSessionMemory()
    success = service.recover_session_state(conv_id, new_session_memory)
    assert success is True
    
    recovered_state = new_session_memory.get_memory(conv_id)
    assert recovered_state.active_document_ids == ["doc_123"]
    assert recovered_state.chunk_ids == ["c1", "c2"]
