import redis
import time
from typing import Dict

class ProviderHealthService:
    def __init__(self, redis_client: redis.Redis, alpha: float = 0.2):
        self.redis = redis_client
        self.alpha = alpha

    def record_metrics(self, provider_id: str, latency: float, success: bool, malformed: bool = False):
        health_key = f"provider:{provider_id}:health"
        current_health = float(self.redis.get(health_key) or 100.0)
        
        penalty = 0.0
        if not success:
            penalty += 30.0
        if malformed:
            penalty += 15.0
            
        event_score = max(0.0, 100.0 - penalty)
        new_health = (self.alpha * event_score) + ((1.0 - self.alpha) * current_health)
        self.redis.set(health_key, str(new_health))

    def get_health_score(self, provider_id: str) -> float:
        health_key = f"provider:{provider_id}:health"
        return float(self.redis.get(health_key) or 100.0)

class ProviderStatusService:
    """
    Tracks real-time availability status, utilizing a local memory cache
    to avoid expensive Redis round-trips on every scheduler iteration.
    """
    def __init__(self, redis_client: redis.Redis, cache_ttl_seconds: float = 1.0):
        self.redis = redis_client
        self.cache_ttl = cache_ttl_seconds
        # Memory Cache: provider_id -> (availability_bool, last_updated_timestamp)
        self._cache: Dict[str, tuple] = {}
        
    def is_available(self, provider_id: str) -> bool:
        now = time.time()
        if provider_id in self._cache:
            val, updated_at = self._cache[provider_id]
            if now - updated_at < self.cache_ttl:
                return val
                
        # Cache miss or expired: Fetch from Redis
        avail_key = f"provider:{provider_id}:available"
        val = self.redis.get(avail_key)
        if val is None:
            is_avail = True
        else:
            if isinstance(val, bytes):
                val = val.decode('utf-8')
            is_avail = (val == "1")
        
        # Write back to local memory cache
        self._cache[provider_id] = (is_avail, now)
        return is_avail

    def mark_unavailable(self, provider_id: str, ttl_seconds: int = 60):
        avail_key = f"provider:{provider_id}:available"
        self.redis.set(avail_key, "0", ex=ttl_seconds)
        self._cache[provider_id] = (False, time.time())

    def mark_available(self, provider_id: str):
        avail_key = f"provider:{provider_id}:available"
        self.redis.set(avail_key, "1")
        self._cache[provider_id] = (True, time.time())
