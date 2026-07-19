import redis
from typing import Optional
from .interfaces import QuotaManager

# Atomic dual-bucket reservation Lua script
LUA_ACQUIRE_QUOTA = """
local rpm_key = KEYS[1]
local rpd_key = KEYS[2]
local concurrent_key = KEYS[3]
local cost = tonumber(ARGV[1])
local max_concurrent = tonumber(ARGV[2])

local rpm_val = tonumber(redis.call('GET', rpm_key) or 0)
local rpd_val = tonumber(redis.call('GET', rpd_key) or 0)
local concurrent_val = tonumber(redis.call('GET', concurrent_key) or 0)

if rpm_val >= cost and rpd_val >= cost and concurrent_val < max_concurrent then
    redis.call('DECRBY', rpm_key, cost)
    redis.call('DECRBY', rpd_key, cost)
    redis.call('INCR', concurrent_key)
    return 1
else
    return 0
"""

class RedisQuotaManager(QuotaManager):
    def __init__(self, redis_client: redis.Redis, max_concurrent: int = 2):
        self.redis = redis_client
        self.acquire_script = self.redis.register_script(LUA_ACQUIRE_QUOTA)
        self.max_concurrent = max_concurrent

    def acquire_quota(self, provider_id: str, cost: int = 1) -> bool:
        keys = [
            f"quota:{provider_id}:rpm",
            f"quota:{provider_id}:rpd",
            f"quota:{provider_id}:concurrent"
        ]
        result = self.acquire_script(keys=keys, args=[cost, self.max_concurrent])
        return result == 1

    def release_quota(self, provider_id: str, cost: int = 1) -> None:
        """
        Releases the concurrency semaphore. RPM/RPD tokens are NOT refunded (they are consumed by the API).
        """
        self.redis.decr(f"quota:{provider_id}:concurrent")
