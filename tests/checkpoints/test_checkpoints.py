import pytest
from backend.infrastructure.storage.memory_storage import MemoryStorage
from backend.infrastructure.storage.checkpoint_store import BinaryCheckpointStore

def test_checkpoint_store():
    storage = MemoryStorage()
    checkpoint_store = BinaryCheckpointStore(storage)
    
    # Empty checkpoint load
    assert checkpoint_store.load_checkpoint(123) == {}
    
    # Save checkpoint
    data = {"completed_pages_count": 5, "checkpoint_version": 1}
    checkpoint_store.save_checkpoint(123, data)
    
    # Load and verify
    loaded = checkpoint_store.load_checkpoint(123)
    assert loaded == data
    
    # Check health
    health = checkpoint_store.health()
    assert health["status"] == "healthy"
    assert health["type"] == "checkpoint_store"
