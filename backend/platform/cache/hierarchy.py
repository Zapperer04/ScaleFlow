import os
import json
import time
import hashlib
from typing import Any, Optional
from collections import OrderedDict
from backend.platform.config.cache import CACHE_TTL, CACHE_ENABLED, L1_MAX_SIZE
from backend.platform.config.settings import settings

class L1Cache:
    """In-memory LRU Cache"""
    def __init__(self, category: str):
        self.capacity = L1_MAX_SIZE.get(category, 500)
        self.cache = OrderedDict()
        self.expiry = {}

    def get(self, key: str) -> Optional[Any]:
        if key not in self.cache:
            return None
        if time.time() > self.expiry.get(key, 0):
            self.delete(key)
            return None
        self.cache.move_to_end(key)
        return self.cache[key]

    def set(self, key: str, value: Any, ttl: int):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        self.expiry[key] = time.time() + ttl
        if len(self.cache) > self.capacity:
            oldest = next(iter(self.cache))
            self.delete(oldest)

    def delete(self, key: str):
        self.cache.pop(key, None)
        self.expiry.pop(key, None)

    def clear(self):
        self.cache.clear()
        self.expiry.clear()


class L3Cache:
    """Disk-backed JSON Cache"""
    def __init__(self, category: str):
        self.dir = os.path.join(settings.CACHE_DIR, category)
        os.makedirs(self.dir, exist_ok=True)

    def _get_path(self, key: str) -> str:
        safe_key = hashlib.sha256(key.encode()).hexdigest()
        return os.path.join(self.dir, f"{safe_key}.json")

    def get(self, key: str) -> Optional[Any]:
        path = self._get_path(key)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if time.time() > data.get("exp", 0):
                os.remove(path)
                return None
            return data.get("val")
        except Exception:
            return None

    def set(self, key: str, value: Any, ttl: int):
        path = self._get_path(key)
        data = {
            "val": value,
            "exp": time.time() + ttl
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception:
            pass

    def delete(self, key: str):
        path = self._get_path(key)
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass

    def clear(self):
        for f in os.listdir(self.dir):
            if f.endswith(".json"):
                try:
                    os.remove(os.path.join(self.dir, f))
                except Exception:
                    pass


class CacheHierarchy:
    def __init__(self):
        self.l1_instances = {}
        self.l3_instances = {}

    def _get_l1(self, category: str) -> L1Cache:
        if category not in self.l1_instances:
            self.l1_instances[category] = L1Cache(category)
        return self.l1_instances[category]

    def _get_l3(self, category: str) -> L3Cache:
        if category not in self.l3_instances:
            self.l3_instances[category] = L3Cache(category)
        return self.l3_instances[category]

    def get(self, category: str, key: str) -> Optional[Any]:
        ttl = CACHE_TTL.get(category, 3600)
        
        # Try L1
        if CACHE_ENABLED["L1"]:
            val = self._get_l1(category).get(key)
            if val is not None:
                return val
                
        # L2 would go here if enabled
        
        # Try L3
        if CACHE_ENABLED["L3"]:
            val = self._get_l3(category).get(key)
            if val is not None:
                # Backfill L1
                if CACHE_ENABLED["L1"]:
                    self._get_l1(category).set(key, val, ttl)
                return val
                
        return None

    def set(self, category: str, key: str, value: Any):
        ttl = CACHE_TTL.get(category, 3600)
        if CACHE_ENABLED["L1"]:
            self._get_l1(category).set(key, value, ttl)
        if CACHE_ENABLED["L3"]:
            self._get_l3(category).set(key, value, ttl)

    def delete(self, category: str, key: str):
        if CACHE_ENABLED["L1"]:
            self._get_l1(category).delete(key)
        if CACHE_ENABLED["L3"]:
            self._get_l3(category).delete(key)

    def flush_all(self):
        for l1 in self.l1_instances.values():
            l1.clear()
        for l3 in self.l3_instances.values():
            l3.clear()
