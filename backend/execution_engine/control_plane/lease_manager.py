import redis
from typing import Optional
from .interfaces import LeaseManager

class RedisLeaseManager(LeaseManager):
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        
    def acquire_lease(self, job_id: str, ttl_seconds: int = 300) -> Optional[str]:
        lease_key = f"lease:{job_id}"
        import uuid
        lease_id = str(uuid.uuid4())
        
        # NX = Set only if not exists
        # EX = Expire in seconds
        acquired = self.redis.set(lease_key, lease_id, nx=True, ex=ttl_seconds)
        
        if acquired:
            return lease_id
        return None
        
    def release_lease(self, job_id: str, lease_id: str) -> bool:
        lease_key = f"lease:{job_id}"
        # Lua script to release ONLY if the lease_id matches
        script = """
        if redis.call("GET", KEYS[1]) == ARGV[1] then
            return redis.call("DEL", KEYS[1])
        else
            return 0
        end
        """
        result = self.redis.eval(script, 1, lease_key, lease_id)
        return result == 1
