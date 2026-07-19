import pytest
import os
import tempfile
import shutil
from backend.infrastructure.storage.filesystem_storage import FilesystemStorage
from backend.infrastructure.storage.memory_storage import MemoryStorage
from backend.infrastructure.storage.artifact_store import ArtifactStore

@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d)

def test_memory_storage():
    storage = MemoryStorage()
    
    # Save & Load
    storage.save_bytes("test.txt", b"hello memory")
    assert storage.load_bytes("test.txt") == b"hello memory"
    assert storage.exists("test.txt") is True
    
    # Overwrite
    storage.save_bytes("test.txt", b"new content")
    assert storage.load_bytes("test.txt") == b"new content"
    
    # Delete
    storage.delete("test.txt")
    assert storage.exists("test.txt") is False
    with pytest.raises(FileNotFoundError):
        storage.load_bytes("test.txt")

def test_filesystem_storage(temp_dir):
    storage = FilesystemStorage(base_dir=temp_dir)
    
    # Save & Load
    storage.save_bytes("sub/test.txt", b"hello filesystem")
    assert storage.load_bytes("sub/test.txt") == b"hello filesystem"
    assert storage.exists("sub/test.txt") is True
    
    # Overwrite
    storage.save_bytes("sub/test.txt", b"new disk content")
    assert storage.load_bytes("sub/test.txt") == b"new disk content"
    
    # Delete
    storage.delete("sub/test.txt")
    assert storage.exists("sub/test.txt") is False
    with pytest.raises(FileNotFoundError):
        storage.load_bytes("sub/test.txt")

def test_artifact_store_wrapper(temp_dir):
    storage = FilesystemStorage(base_dir=temp_dir)
    store = ArtifactStore(storage)
    
    store.save_artifact("artifacts/art1.json", b'{"key": "value"}')
    assert store.load_artifact("artifacts/art1.json") == b'{"key": "value"}'
    
    health_info = store.health()
    assert health_info["status"] == "healthy"
    assert health_info["type"] == "artifact_store"
