import redis
import time
from typing import Dict, Optional
from collections import deque
import threading
import logging

logger = logging.getLogger("ProviderHealth")


class ProviderHealthService:
    """
    Task 4: Enhanced health scoring that incorporates:
    - latency (EWMA)
    - timeout rate
    - retry success rate
    - 429 frequency
    - recovery rate after cooldown
    Decays old observations so providers are never permanently penalized.
    """

    def __init__(self, redis_client: redis.Redis, alpha: float = 0.15):
        self.redis = redis_client
        self.alpha = alpha  # EWMA smoothing factor (smaller = slower to react)
        # In-memory metrics per provider for sub-Redis granularity
        self._local: Dict[str, dict] = {}
        self._lock = threading.Lock()

    def _local_state(self, provider_id: str) -> dict:
        with self._lock:
            if provider_id not in self._local:
                self._local[provider_id] = {
                    "latencies": deque(maxlen=20),
                    "timeout_count": 0,
                    "retry_success_count": 0,
                    "retry_total_count": 0,
                    "rate_429_count": 0,
                    "request_count": 0,
                    "recovery_count": 0,
                    "cooldown_count": 0,
                }
            return self._local[provider_id]

    def record_metrics(
        self,
        provider_id: str,
        latency: float,
        success: bool,
        malformed: bool = False,
        is_429: bool = False,
        is_timeout: bool = False,
        was_retry: bool = False,
        recovered_from_cooldown: bool = False,
    ):
        state = self._local_state(provider_id)
        with self._lock:
            state["request_count"] += 1
            state["latencies"].append(latency)

            if is_429:
                state["rate_429_count"] += 1
            if is_timeout:
                state["timeout_count"] += 1
            if was_retry:
                state["retry_total_count"] += 1
                if success:
                    state["retry_success_count"] += 1
            if recovered_from_cooldown and success:
                state["recovery_count"] += 1

        health_key = f"provider:{provider_id}:health"
        current_health = float(self.redis.get(health_key) or 100.0)

        penalty = 0.0
        bonus = 0.0

        if not success:
            penalty += 25.0
        if malformed:
            penalty += 15.0
        if is_429:
            penalty += 10.0   # 429 is soft — recoverable
        if is_timeout:
            penalty += 20.0
        if recovered_from_cooldown and success:
            bonus += 10.0     # Reward recovery
        if was_retry and success:
            bonus += 5.0      # Retry success is a positive signal

        event_score = max(0.0, min(100.0, 100.0 - penalty + bonus))
        new_health = (self.alpha * event_score) + ((1.0 - self.alpha) * current_health)

        # Decay toward 100 when healthy to avoid permanent penalties
        if new_health > 80.0:
            decay_boost = 0.01 * (100.0 - new_health)
            new_health = min(100.0, new_health + decay_boost)

        self.redis.set(health_key, str(new_health))
        logger.debug(f"[Health] {provider_id}: score={new_health:.1f} (penalty={penalty:.1f}, bonus={bonus:.1f})")

    def get_health_score(self, provider_id: str) -> float:
        health_key = f"provider:{provider_id}:health"
        return float(self.redis.get(health_key) or 100.0)

    def get_detailed_health(self, provider_id: str) -> dict:
        score = self.get_health_score(provider_id)
        state = self._local_state(provider_id)
        with self._lock:
            latencies = list(state["latencies"])
            avg_lat = sum(latencies) / len(latencies) if latencies else 0.0
            timeout_rate = (state["timeout_count"] / max(1, state["request_count"]))
            rate_429 = (state["rate_429_count"] / max(1, state["request_count"]))
            retry_success_rate = (
                state["retry_success_count"] / max(1, state["retry_total_count"])
                if state["retry_total_count"] > 0
                else 1.0
            )
            return {
                "provider_id": provider_id,
                "health_score": round(score, 2),
                "avg_latency_sec": round(avg_lat, 3),
                "timeout_rate": round(timeout_rate, 4),
                "rate_429": round(rate_429, 4),
                "retry_success_rate": round(retry_success_rate, 4),
                "recovery_count": state["recovery_count"],
                "request_count": state["request_count"],
            }


class ProviderStatusService:
    """
    Tracks real-time availability status.
    Integrates with circuit breaker and cooldown scheduler.
    Uses local memory cache to reduce Redis round-trips.
    Every rejection is explained via a reason string.
    """

    def __init__(self, redis_client: redis.Redis, cache_ttl_seconds: float = 1.0):
        self.redis = redis_client
        self.cache_ttl = cache_ttl_seconds
        self._cache: Dict[str, tuple] = {}
        self._rejection_reasons: Dict[str, str] = {}

    def is_available(self, provider_id: str) -> bool:
        return self.get_availability(provider_id)[0]

    def get_availability(self, provider_id: str) -> tuple:
        """Returns (is_available: bool, rejection_reason: str)."""
        now = time.time()
        if provider_id in self._cache:
            val, updated_at = self._cache[provider_id]
            if now - updated_at < self.cache_ttl:
                return val, self._rejection_reasons.get(provider_id, "")

        avail_key = f"provider:{provider_id}:available"
        val = self.redis.get(avail_key)
        if val is None:
            is_avail = True
        else:
            if isinstance(val, bytes):
                val = val.decode("utf-8")
            is_avail = val == "1"

        reason = "" if is_avail else self._rejection_reasons.get(provider_id, "marked_unavailable")
        self._cache[provider_id] = (is_avail, now)
        return is_avail, reason

    def mark_unavailable(self, provider_id: str, ttl_seconds: int = 60, reason: str = "quota_exhausted"):
        avail_key = f"provider:{provider_id}:available"
        self.redis.set(avail_key, "0", ex=ttl_seconds)
        self._cache[provider_id] = (False, time.time())
        self._rejection_reasons[provider_id] = reason
        logger.info(f"[Status] {provider_id} marked UNAVAILABLE for {ttl_seconds}s ({reason})")

    def mark_available(self, provider_id: str):
        avail_key = f"provider:{provider_id}:available"
        self.redis.set(avail_key, "1")
        self._cache[provider_id] = (True, time.time())
        self._rejection_reasons.pop(provider_id, None)
        logger.info(f"[Status] {provider_id} marked AVAILABLE")

    def get_rejection_reason(self, provider_id: str) -> str:
        return self._rejection_reasons.get(provider_id, "")
