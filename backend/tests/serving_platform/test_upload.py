import os
import sys
import pytest
import sqlite3
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from backend.platform.services.document_service import DocumentService
from backend.platform.storage.document_store import DocumentStore

@pytest.fixture
def temp_db_and_store():
    # Setup in-memory temp DB and folder
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE documents (
        id TEXT PRIMARY KEY,
        filename TEXT NOT NULL,
        filepath TEXT NOT NULL,
        state TEXT NOT NULL,
        parser_version TEXT,
        embedding_version TEXT,
        chunk_version TEXT,
        graph_version TEXT,
        index_version TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    
    store = DocumentStore()
    yield conn, store
    conn.close()

def test_document_registration_and_lifecycle(temp_db_and_store):
    conn, store = temp_db_and_store
    service = DocumentService(conn, store)
    
    doc_id = "test_doc_hash_123"
    filename = "document.pdf"
    filepath = "/fake/path/document.pdf"
    
    # 1. Register Uploaded
    doc = service.register_document(doc_id, filename, filepath)
    assert doc["id"] == doc_id
    assert doc["state"] == "UPLOADED"
    
    # 2. Check Lock
    assert service.check_and_lock_document(doc_id) is True
    
    # 3. Transition to Indexing
    service.update_state(doc_id, "INDEXING")
    doc = service.get_document(doc_id)
    assert doc["state"] == "INDEXING"
    
    # Check Lock when Indexing (must be locked)
    assert service.check_and_lock_document(doc_id) is False
    
    # 4. Transition to Indexed with version metadata
    versions = {
        "parser_version": "1.0.0",
        "embedding_version": "1.0.0",
        "chunk_version": "1.0.0",
        "graph_version": "1.0.0",
        "index_version": "1.0.0"
    }
    service.update_state(doc_id, "INDEXED", versions=versions)
    doc = service.get_document(doc_id)
    assert doc["state"] == "INDEXED"
    assert doc["parser_version"] == "1.0.0"
    
    # 5. Delete document
    success = service.delete_document(doc_id)
    assert success is True
    assert service.get_document(doc_id) is None
