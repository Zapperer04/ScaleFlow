import time
import logging
from collections import OrderedDict
from typing import Any, Optional, Dict

logger = logging.getLogger(__name__)

class LRUCache:
    def __init__(self, capacity: int = 1000):
        self.cache = OrderedDict()
        self.capacity = capacity
        self.expiry = {}
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        now = time.time()
        if key in self.cache:
            # Check expiry
            if key in self.expiry and self.expiry[key] < now:
                self.delete(key)
                self.misses += 1
                return None
            
            # Move to end to indicate recent use
            self.cache.move_to_end(key)
            self.hits += 1
            return self.cache[key]
        self.misses += 1
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        now = time.time()
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if ttl is not None:
            self.expiry[key] = now + ttl
        else:
            self.expiry.pop(key, None)

        if len(self.cache) > self.capacity:
            # Evict oldest
            oldest, _ = self.cache.popitem(last=False)
            self.expiry.pop(oldest, None)

    def delete(self, key: str) -> None:
        self.cache.pop(key, None)
        self.expiry.pop(key, None)

    def clear(self) -> None:
        self.cache.clear()
        self.expiry.clear()

    def get_stats(self) -> dict:
        total = self.hits + self.misses
        ratio = self.hits / total if total > 0 else 0.0
        return {
            "size": len(self.cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_ratio": round(ratio, 4)
        }


class CacheManager:
    def __init__(self):
        # Cache namespaces
        self.namespaces = [
            "replay", "performance", "optimization", "forecast", "advisor",
            "document", "embedding", "query", "graph", "chunk", "context"
        ]
        self.caches: Dict[str, LRUCache] = {ns: LRUCache(capacity=500) for ns in self.namespaces}

    def get(self, namespace: str, key: str) -> Optional[Any]:
        if namespace not in self.caches:
            logger.warning(f"Unknown cache namespace requested: {namespace}")
            return None
        return self.caches[namespace].get(key)

    def set(self, namespace: str, key: str, value: Any, ttl: Optional[int] = None) -> None:
        if namespace not in self.caches:
            logger.warning(f"Unknown cache namespace requested: {namespace}")
            return
        self.caches[namespace].set(key, value, ttl=ttl)

    def invalidate(self, namespace: str, key: str) -> None:
        if namespace in self.caches:
            self.caches[namespace].delete(key)

    def invalidate_all(self, namespace: str) -> None:
        if namespace in self.caches:
            self.caches[namespace].clear()

    def get_namespace_stats(self, namespace: str) -> dict:
        if namespace in self.caches:
            return self.caches[namespace].get_stats()
        return {}

    def get_all_stats(self) -> dict:
        return {ns: self.caches[ns].get_stats() for ns in self.namespaces}

    def invalidate_entire_cache(self) -> None:
        for ns in self.namespaces:
            self.caches[ns].clear()

cache_manager = CacheManager()
