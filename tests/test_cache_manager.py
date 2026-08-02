import pytest
import time
from backend.cache_manager import cache_manager, LRUCache

def test_lru_cache_expiry():
    cache = LRUCache(capacity=2)
    # Set with immediate expiration
    cache.set("a", 1, ttl=1)
    assert cache.get("a") == 1
    
    # Wait for TTL expiry
    time.sleep(1.1)
    assert cache.get("a") is None

def test_lru_cache_eviction():
    cache = LRUCache(capacity=2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)  # Evicts "a"
    
    assert cache.get("a") is None
    assert cache.get("b") == 2
    assert cache.get("c") == 3

def test_cache_manager_namespaces():
    cache_manager.set("query", "k1", "val1")
    cache_manager.set("performance", "k1", "val2")
    
    assert cache_manager.get("query", "k1") == "val1"
    assert cache_manager.get("performance", "k1") == "val2"
    
    # Invalidate query only
    cache_manager.invalidate("query", "k1")
    assert cache_manager.get("query", "k1") is None
    assert cache_manager.get("performance", "k1") == "val2"
    
    # Check stats
    stats = cache_manager.get_all_stats()
    assert "query" in stats
    assert "performance" in stats
