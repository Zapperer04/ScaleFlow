import os
import sys
import pytest
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.document_pipeline.registry.registry import DocumentRegistry

@pytest.fixture
def temp_db_path():
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_registry.db")
    yield db_path
    shutil.rmtree(temp_dir)

def test_document_registry_operations(temp_db_path):
    registry = DocumentRegistry(db_path=temp_db_path)
    
    doc_id = "test-doc-id-123"
    versions = {"chunks": "1.0.0", "embeddings": "2.0.0"}
    hashes = {"chunks": "abc123hash"}
    dependencies = {"embeddings": ["chunks"]}
    available = ["chunks", "embeddings"]
    outputs = {"parser": "vlm"}
    
    # Register
    registry.register_document(doc_id, versions, hashes, dependencies, available, outputs)
    
    # Retrieve
    retrieved = registry.get_document(doc_id)
    assert retrieved is not None
    assert retrieved["document_id"] == doc_id
    assert retrieved["versions"]["chunks"] == "1.0.0"
    assert retrieved["hashes"]["chunks"] == "abc123hash"
    assert retrieved["dependencies"]["embeddings"] == ["chunks"]
    assert "chunks" in retrieved["available_representations"]
    
    # List
    docs = registry.list_documents()
    assert len(docs) == 1
    assert docs[0]["document_id"] == doc_id

def test_document_registry_recovery(temp_db_path):
    # Initialize DB, write record
    registry = DocumentRegistry(db_path=temp_db_path)
    registry.register_document("doc-1", {}, {}, {}, [], {})
    
    # Create new registry instance pointing to same file
    registry2 = DocumentRegistry(db_path=temp_db_path)
    retrieved = registry2.get_document("doc-1")
    assert retrieved is not None
    assert retrieved["document_id"] == "doc-1"
