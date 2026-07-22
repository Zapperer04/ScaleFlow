import time
from typing import Dict, List
from backend.platform.config.settings import settings

class RateLimiter:
    def __init__(self):
        # Maps key -> list of request timestamps
        self.history: Dict[str, List[float]] = {}

    def is_rate_limited(self, key: str, max_requests: int = None, window_seconds: int = 60) -> bool:
        limit = max_requests or settings.DEFAULT_RATE_LIMIT_RPM
        now = time.time()
        
        if key not in self.history:
            self.history[key] = []
            
        # Clean up timestamps older than window
        self.history[key] = [t for t in self.history[key] if now - t < window_seconds]
        
        if len(self.history[key]) >= limit:
            return True
            
        self.history[key].append(now)
        return False

rate_limiter = RateLimiter()
