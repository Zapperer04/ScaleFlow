import json
import logging
from typing import Any, Optional
import redis
from backend.infrastructure.storage.cache_store import BaseCacheStore

logger = logging.getLogger(__name__)

class RedisCache(BaseCacheStore):
    """Redis-backed implementation of BaseCacheStore."""

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.client = redis.Redis(host=host, port=port, db=db, decode_responses=True)

    def get(self, key: str) -> Optional[Any]:
        try:
            val = self.client.get(key)
            if val is not None:
                try:
                    return json.loads(val)
                except json.JSONDecodeError:
                    return val
            return None
        except Exception as e:
            logger.warning(f"Redis get failed for {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        try:
            val_str = json.dumps(value) if not isinstance(value, str) else value
            self.client.set(key, val_str, ex=ttl)
        except Exception as e:
            logger.warning(f"Redis set failed for {key}: {e}")

    def invalidate(self, key: str) -> None:
        try:
            self.client.delete(key)
        except Exception as e:
            logger.warning(f"Redis delete failed for {key}: {e}")

    def health(self) -> dict:
        try:
            self.client.ping()
            return {"status": "healthy", "type": "redis"}
        except Exception as e:
            return {"status": "unhealthy", "type": "redis", "error": str(e)}
