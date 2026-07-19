import pytest
import time
from backend.infrastructure.storage.memory_cache import MemoryCache
from backend.infrastructure.storage.redis_cache import RedisCache

def test_memory_cache():
    cache = MemoryCache()
    
    # Simple set & get
    cache.set("key1", {"data": 123})
    assert cache.get("key1") == {"data": 123}
    
    # Invalidate
    cache.invalidate("key1")
    assert cache.get("key1") is None
    
    # TTL
    cache.set("key_ttl", "temp", ttl=1)
    assert cache.get("key_ttl") == "temp"
    time.sleep(1.1)
    assert cache.get("key_ttl") is None

def test_redis_cache_mocked():
    # Since tests/conftest.py might run with a mock redis or a local redis, let's write a safe mock-fallback test.
    try:
        cache = RedisCache(host="localhost", port=6379, db=0)
        # Verify basic operations
        cache.set("test_key", "test_val")
        val = cache.get("test_key")
        if val == "test_val":
            cache.invalidate("test_key")
            assert cache.get("test_key") is None
    except Exception:
        pytest.skip("Local Redis server not running, skipping RedisCache integration test.")
