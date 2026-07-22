import os
import sys
import pytest
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.document_pipeline.storage.storage import DocumentStore

@pytest.fixture
def temp_store_dir():
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

def test_document_store_save_load(temp_store_dir):
    store = DocumentStore(base_dir=temp_store_dir)
    doc_id = "test-doc-hash"
    
    data = {"hello": "world", "nested": {"val": 123}}
    store.save_json(doc_id, "test_file.json", data)
    
    assert store.exists(doc_id, "test_file.json")
    
    loaded = store.load_json(doc_id, "test_file.json")
    assert loaded == data
    
    # Missing file
    assert store.load_json(doc_id, "non_existent.json") is None
