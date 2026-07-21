"""
AdaptiveRateLimitManager — Task 1 of Phase 2C
Per-provider quota tracking with moving averages, adaptive pacing, and burst capacity.
Replaces fixed delays with evidence-based scheduling.
"""
import time
import threading
import collections
from typing import Dict, Optional, Tuple

import logging

logger = logging.getLogger("AdaptiveRateLimitManager")


class ProviderQuotaState:
    """Observed rate statistics for a single provider."""

    def __init__(self, provider_id: str, observed_rpm_cap: int = 15):
        self.provider_id = provider_id
        self.observed_rpm_cap = observed_rpm_cap  # Confirmed stable RPM

        # Rolling window: timestamps of successful requests (last 60 s)
        self._request_timestamps: collections.deque = collections.deque()
        self._lock = threading.Lock()

        # Moving 429 rate — sliding window of the last 20 attempts
        self._attempt_outcomes: collections.deque = collections.deque(maxlen=20)

        # Retry delay observations (seconds)
        self._retry_delays: collections.deque = collections.deque(maxlen=10)

        # Burst capacity (tokens above the steady-state RPM)
        self.burst_capacity = max(1, observed_rpm_cap // 3)

        # Cooldown tracking
        self.cooldown_until: float = 0.0
        self.cooldown_count: int = 0

        # TPM tracking (approximate)
        self._token_timestamps: collections.deque = collections.deque()

        # Rolling histories for broker statistics
        self._latencies: collections.deque = collections.deque(maxlen=20)
        self._queue_waits: collections.deque = collections.deque(maxlen=20)

    # ------------------------------------------------------------------
    # Request tracking
    # ------------------------------------------------------------------

    def record_request(self, tokens: int = 0):
        now = time.time()
        with self._lock:
            self._request_timestamps.append(now)
            self._attempt_outcomes.append(True)
            if tokens > 0:
                self._token_timestamps.append((now, tokens))

    def record_429(self, retry_after: float = 0.0):
        with self._lock:
            self._attempt_outcomes.append(False)
            if retry_after > 0.0:
                self._retry_delays.append(retry_after)

    # ------------------------------------------------------------------
    # Computed properties
    # ------------------------------------------------------------------

    def observed_rpm(self) -> float:
        """Count requests in the last 60 seconds."""
        now = time.time()
        with self._lock:
            cutoff = now - 60.0
            while self._request_timestamps and self._request_timestamps[0] < cutoff:
                self._request_timestamps.popleft()
            return float(len(self._request_timestamps))

    def observed_tpm(self) -> float:
        """Approximate tokens per minute."""
        now = time.time()
        with self._lock:
            cutoff = now - 60.0
            while self._token_timestamps and self._token_timestamps[0][0] < cutoff:
                self._token_timestamps.popleft()
            return float(sum(t for _, t in self._token_timestamps))

    def moving_429_rate(self) -> float:
        """Fraction of recent attempts that were 429s."""
        with self._lock:
            if not self._attempt_outcomes:
                return 0.0
            failures = sum(1 for ok in self._attempt_outcomes if not ok)
            return failures / len(self._attempt_outcomes)

    def average_retry_delay(self) -> float:
        with self._lock:
            if not self._retry_delays:
                return 0.0
            return sum(self._retry_delays) / len(self._retry_delays)

    def in_cooldown(self) -> bool:
        return time.time() < self.cooldown_until

    def cooldown_remaining(self) -> float:
        return max(0.0, self.cooldown_until - time.time())

    # ------------------------------------------------------------------
    # Adaptive pacing
    # ------------------------------------------------------------------

    def required_inter_request_gap(self) -> float:
        """
        Compute the minimum gap (seconds) to never exceed the stable RPM.
        The gap widens when the 429 rate is elevated.
        """
        stable_rpm = max(1, self.observed_rpm_cap)
        base_gap = 60.0 / stable_rpm

        rate_429 = self.moving_429_rate()
        if rate_429 > 0.5:
            # Severe quota pressure — back off hard
            return base_gap * 4.0
        elif rate_429 > 0.25:
            return base_gap * 2.0
        elif rate_429 > 0.1:
            return base_gap * 1.5
        return base_gap

    def can_request_now(self) -> Tuple[bool, float]:
        """
        Returns (allowed, wait_seconds).
        Uses the adaptive pacing gap to decide if a new request is safe.
        """
        if self.in_cooldown():
            return False, self.cooldown_remaining()

        now = time.time()
        gap = self.required_inter_request_gap()
        with self._lock:
            if self._request_timestamps:
                last_req = self._request_timestamps[-1]
                elapsed = now - last_req
                if elapsed < gap:
                    return False, gap - elapsed
        return True, 0.0

    def to_dict(self) -> dict:
        return {
            "provider_id": self.provider_id,
            "observed_rpm": round(self.observed_rpm(), 2),
            "observed_rpm_cap": self.observed_rpm_cap,
            "observed_tpm": round(self.observed_tpm(), 2),
            "moving_429_rate": round(self.moving_429_rate(), 4),
            "average_retry_delay_sec": round(self.average_retry_delay(), 2),
            "burst_capacity": self.burst_capacity,
            "in_cooldown": self.in_cooldown(),
            "cooldown_remaining_sec": round(self.cooldown_remaining(), 2),
            "cooldown_count": self.cooldown_count,
            "inter_request_gap_sec": round(self.required_inter_request_gap(), 3),
        }


class AdaptiveRateLimitManager:
    """
    Maintains ProviderQuotaState for each provider.
    Provides the single authority for: can I make a request now?
    """

    def __init__(self):
        self._states: Dict[str, ProviderQuotaState] = {}
        self._lock = threading.Lock()
        self._broker = None
        self.enable_persistence = True
        self._load_state_from_disk()

    def register_broker(self, broker):
        self._broker = broker

    def _load_state_from_disk(self):
        import json
        import os
        import sys
        if not self.enable_persistence:
            return
        if "pytest" in sys.modules:
            # Check if we explicitly forced it
            if getattr(self, "_force_pytest_persistence", False) is False:
                return
        path = "reports/provider_runtime_state.json"
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                # Populate default providers first
                for pid in ["gemini", "openrouter"]:
                    self._get_or_create(pid)
                for pid, sdata in data.items():
                    state = self._get_or_create(pid)
                    state.observed_rpm_cap = sdata.get("observed_rpm_cap", state.observed_rpm_cap)
                    state.cooldown_count = sdata.get("cooldown_count", state.cooldown_count)
                    remaining_cooldown = sdata.get("cooldown_remaining_sec", 0.0)
                    if remaining_cooldown > 0.0:
                        state.cooldown_until = time.time() + remaining_cooldown
                    
                    outcomes = sdata.get("attempt_outcomes", [])
                    state._attempt_outcomes.clear()
                    state._attempt_outcomes.extend(outcomes)

                    delays = sdata.get("retry_delays", [])
                    state._retry_delays.clear()
                    state._retry_delays.extend(delays)

                    latencies = sdata.get("latencies", [])
                    state._latencies.clear()
                    state._latencies.extend(latencies)

                    queue_waits = sdata.get("queue_waits", [])
                    state._queue_waits.clear()
                    state._queue_waits.extend(queue_waits)
                    
                    health_val = sdata.get("health")
                    if health_val is not None:
                        try:
                            import redis
                            r = redis.Redis(host="localhost", port=6380, db=0, decode_responses=True)
                            r.set(f"provider:{pid}:health", str(health_val * 100.0 if health_val <= 1.0 else health_val))
                        except Exception:
                            pass
                logger.info(f"Loaded provider runtime state from {path}")
            except Exception as e:
                logger.error(f"Failed to load provider runtime state: {e}")

    def _save_state_to_disk(self):
        import json
        import os
        import sys
        if not self.enable_persistence:
            return
        if "pytest" in sys.modules:
            # Check if we explicitly forced it
            if getattr(self, "_force_pytest_persistence", False) is False:
                return
        path = "reports/provider_runtime_state.json"
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            data = {}
            for pid, state in self._states.items():
                health = 100.0
                try:
                    import redis
                    r = redis.Redis(host="localhost", port=6380, db=0, decode_responses=True)
                    val = r.get(f"provider:{pid}:health")
                    if val is not None:
                        health = float(val)
                except Exception:
                    pass

                avg_lat = sum(state._latencies) / len(state._latencies) if state._latencies else 0.0
                avg_qw = sum(state._queue_waits) / len(state._queue_waits) if state._queue_waits else 0.0

                broker_selected = 0
                broker_rejected = 0
                selection_rate = 0.0
                if getattr(self, "_broker", None) is not None:
                    try:
                        history = self._broker.get_routing_history()
                        broker_selected = sum(1 for d in history if d.get("selected_provider") == pid)
                        broker_rejected = sum(1 for d in history if pid in d.get("providers_rejected", {}))
                        selection_rate = round(broker_selected / max(1, broker_selected + broker_rejected) * 100.0, 1)
                    except Exception:
                        pass

                cb_dict = {}
                try:
                    from execution_engine.control_plane.circuit_breaker import get_circuit_registry
                    cb_dict = get_circuit_registry().get(pid).to_dict()
                except Exception:
                    pass

                data[pid] = {
                    "observed_rpm": round(state.observed_rpm(), 2),
                    "observed_rpm_cap": state.observed_rpm_cap,
                    "cooldown": round(state.cooldown_remaining(), 2),
                    "429_rate": round(state.moving_429_rate(), 4),
                    "health": round(health / 100.0, 2) if health <= 100.0 else health,
                    "cooldown_remaining_sec": round(state.cooldown_remaining(), 2),
                    "cooldown_count": state.cooldown_count,
                    "attempt_outcomes": list(state._attempt_outcomes),
                    "retry_delays": list(state._retry_delays),
                    "last_success": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()) if state._attempt_outcomes and state._attempt_outcomes[-1] else "N/A",
                    "last_failure": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()) if state._attempt_outcomes and not state._attempt_outcomes[-1] else "N/A",
                    "avg_latency_ms": round(avg_lat, 1),
                    "avg_queue_wait_ms": round(avg_qw, 1),
                    "breaker_open_count": cb_dict.get("open_count", 0),
                    "breaker_half_open_success": cb_dict.get("recovery_count", 0),
                    "broker_selected": broker_selected,
                    "broker_rejected": broker_rejected,
                    "selection_rate": selection_rate,
                    "latencies": list(state._latencies),
                    "queue_waits": list(state._queue_waits),
                }
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save provider runtime state: {e}")

    def _get_or_create(self, provider_id: str) -> ProviderQuotaState:
        with self._lock:
            if provider_id not in self._states:
                # Known stable caps
                caps = {"gemini": 15, "openrouter": 20}
                cap = caps.get(provider_id, 10)
                self._states[provider_id] = ProviderQuotaState(provider_id, cap)
            return self._states[provider_id]

    def can_request(self, provider_id: str) -> Tuple[bool, float]:
        """Returns (allowed, wait_seconds_if_denied)."""
        return self._get_or_create(provider_id).can_request_now()

    def record_success(self, provider_id: str, tokens: int = 0, latency_ms: float = 0.0, queue_wait_ms: float = 0.0):
        state = self._get_or_create(provider_id)
        state.record_request(tokens)
        if latency_ms > 0:
            state._latencies.append(latency_ms)
        if queue_wait_ms > 0:
            state._queue_waits.append(queue_wait_ms)
        self._save_state_to_disk()

    def record_429(self, provider_id: str, retry_after: float = 0.0):
        self._get_or_create(provider_id).record_429(retry_after)
        self._save_state_to_disk()

    def apply_cooldown(self, provider_id: str, duration: float):
        state = self._get_or_create(provider_id)
        state.cooldown_until = time.time() + duration
        state.cooldown_count += 1
        logger.info(f"[AdaptiveRateManager] {provider_id} cooldown={duration:.1f}s "
                    f"(total cooldowns={state.cooldown_count})")
        self._save_state_to_disk()

    def get_state(self, provider_id: str) -> ProviderQuotaState:
        return self._get_or_create(provider_id)

    def all_provider_ids(self):
        with self._lock:
            return list(self._states.keys())

    def to_dashboard(self) -> dict:
        with self._lock:
            return {pid: s.to_dict() for pid, s in self._states.items()}


# Singleton
_adaptive_rate_manager: Optional[AdaptiveRateLimitManager] = None
_arl_lock = threading.Lock()


def get_adaptive_rate_manager() -> AdaptiveRateLimitManager:
    global _adaptive_rate_manager
    with _arl_lock:
        if _adaptive_rate_manager is None:
            _adaptive_rate_manager = AdaptiveRateLimitManager()
        return _adaptive_rate_manager
