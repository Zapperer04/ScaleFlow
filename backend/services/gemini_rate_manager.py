import os
import time
import random
import threading
import redis
from typing import Optional, Tuple, Dict, Any

class GeminiRateManager:
    """
    Central Gemini Rate Manager.
    Coordinates rate limiting, cooldown, and provider-aware exponential backoff with jitter.
    Uses Redis if available for sharing state across workers, falls back to in-memory thread-safe state.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(GeminiRateManager, cls).__new__(cls, *args, **kwargs)
                cls._instance._init_manager()
            return cls._instance

    def _init_manager(self):
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("REDIS_PORT", 6379))
        self.redis_client = None
        self._local_state = {
            "cooldown_until": 0.0,
            "backoff_level": 0,
            "requests_sent": 0,
            "429_count": 0,
            "total_pause_duration": 0.0,
            "last_pause_start": 0.0
        }
        self._local_lock = threading.Lock()

        # Attempt to initialize Redis client
        try:
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                decode_responses=True,
                socket_timeout=2,
                socket_connect_timeout=2
            )
            # Ping to verify connection
            self.redis_client.ping()
        except Exception:
            self.redis_client = None

    def _get_key(self, name: str) -> str:
        return f"gemini:rate_manager:{name}"

    def _get_value(self, name: str, default: Any) -> Any:
        if self.redis_client:
            try:
                val = self.redis_client.get(self._get_key(name))
                if val is not None:
                    if isinstance(default, float):
                        return float(val)
                    if isinstance(default, int):
                        return int(val)
                    return val
            except Exception:
                pass
        with self._local_lock:
            return self._local_state.get(name, default)

    def _set_value(self, name: str, value: Any, expire_seconds: Optional[int] = None):
        if self.redis_client:
            try:
                key = self._get_key(name)
                self.redis_client.set(key, str(value), ex=expire_seconds)
            except Exception:
                pass
        with self._local_lock:
            self._local_state[name] = value

    def _incr_value(self, name: str, amount: int = 1) -> int:
        if self.redis_client:
            try:
                key = self._get_key(name)
                return int(self.redis_client.incrby(key, amount))
            except Exception:
                pass
        with self._local_lock:
            self._local_state[name] = self._local_state.get(name, 0) + amount
            return self._local_state[name]

    def check_availability(self) -> Tuple[bool, float]:
        """
        Returns (is_available, cooldown_remaining_seconds)
        """
        cooldown_until = self._get_value("cooldown_until", 0.0)
        now = time.time()
        if now < cooldown_until:
            return False, max(0.0, cooldown_until - now)
        return True, 0.0

    def register_success(self):
        """Reset exponential backoff level on a successful request."""
        self._set_value("backoff_level", 0)
        self._incr_value("requests_sent")

    def register_429(self, retry_after_header: Optional[str] = None) -> float:
        """
        Registers a 429 response. Computes backoff duration, updates cooldown state, and returns pause seconds.
        """
        self._incr_value("429_count")
        
        # 1. Check Retry-After header
        retry_after = 0.0
        if retry_after_header:
            try:
                # Retry-After could be an integer (seconds) or a HTTP-date string
                retry_after = float(retry_after_header)
            except ValueError:
                # If date, try parsing it, fallback to default if parsing fails
                retry_after = 60.0

        # 2. Provider-aware Backoff / Exponential with Jitter
        if retry_after <= 0.0:
            backoff_level = self._incr_value("backoff_level")
            # Base backoff starts at 5s, doubling each time, capped at 300s, plus random jitter
            base_duration = 5.0 * (1.5 ** (backoff_level - 1))
            jitter = random.uniform(0.5, 2.0)
            retry_after = min(300.0, base_duration * jitter)

        now = time.time()
        new_cooldown_until = now + retry_after
        
        # If there's an existing cooldown, only extend it if new is further
        current_cooldown = self._get_value("cooldown_until", 0.0)
        if new_cooldown_until > current_cooldown:
            self._set_value("cooldown_until", new_cooldown_until)
            # Track pause duration
            pause_dur = retry_after
            self._incr_value("total_pause_duration", int(pause_dur))

        return retry_after

    def get_metrics(self) -> Dict[str, Any]:
        availability, cooldown = self.check_availability()
        return {
            "requests_sent": self._get_value("requests_sent", 0),
            "429_count": self._get_value("429_count", 0),
            "total_pause_duration": self._get_value("total_pause_duration", 0.0),
            "cooldown_remaining": round(cooldown, 1),
            "status": "PAUSED_RATE_LIMIT" if not availability else "RUNNING"
        }

    def wait_if_needed(self, trace_fn = None) -> None:
        """
        Blocks the calling thread if Gemini is in cooldown.
        """
        while True:
            available, remaining = self.check_availability()
            if available:
                break
            if trace_fn:
                trace_fn(f"[Rate Manager] Waiting {remaining:.1f} seconds for Gemini cooldown...")
            time.sleep(min(remaining, 5.0))
