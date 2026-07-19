import time
import copy
from typing import Any, Optional, Dict, Tuple
from backend.infrastructure.storage.cache_store import BaseCacheStore

class MemoryCache(BaseCacheStore):
    """In-memory cache implementation with TTL support."""

    def __init__(self):
        # Format: {key: (value, expiry_timestamp)}
        self.store: Dict[str, Tuple[Any, Optional[float]]] = {}

    def get(self, key: str) -> Optional[Any]:
        if key not in self.store:
            return None
        val, expiry = self.store[key]
        if expiry is not None and time.time() > expiry:
            del self.store[key]
            return None
        return copy.deepcopy(val)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        expiry = time.time() + ttl if ttl is not None else None
        self.store[key] = (copy.deepcopy(value), expiry)

    def invalidate(self, key: str) -> None:
        if key in self.store:
            del self.store[key]

    def health(self) -> dict:
        # Clean expired items
        now = time.time()
        expired = [k for k, (_, exp) in self.store.items() if exp is not None and now > exp]
        for k in expired:
            del self.store[k]
        return {"status": "healthy", "type": "memory", "size": len(self.store)}
