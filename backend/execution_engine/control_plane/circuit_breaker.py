"""
CircuitBreaker — Task 2 & 3 of Phase 2C
Three-state machine: Closed → Open → Half-Open → Closed
Integrates with AdaptiveCooldownScheduler for 429-based cooldown estimation.
"""
import time
import threading
import logging
from enum import Enum, auto
from typing import Dict, Optional, List
from collections import deque

logger = logging.getLogger("CircuitBreaker")


class CircuitState(Enum):
    CLOSED = auto()       # Normal operation — requests allowed
    OPEN = auto()         # Failure threshold exceeded — requests blocked
    HALF_OPEN = auto()    # Probe allowed — testing recovery


class CircuitTransition:
    def __init__(self, from_state: CircuitState, to_state: CircuitState, reason: str):
        self.from_state = from_state
        self.to_state = to_state
        self.reason = reason
        self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            "from_state": self.from_state.name,
            "to_state": self.to_state.name,
            "reason": self.reason,
            "timestamp": round(self.timestamp, 3),
            "iso_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.timestamp)),
        }


class ProviderCircuitBreaker:
    """
    Per-provider circuit breaker with adaptive cooldown.
    Opens after `failure_threshold` consecutive failures.
    Transitions to HALF_OPEN after `reset_timeout_sec`.
    Closes after `probe_successes` consecutive successful probes.
    """

    def __init__(
        self,
        provider_id: str,
        failure_threshold: int = 5,
        probe_successes: int = 2,
        base_reset_timeout_sec: float = 60.0,
    ):
        self.provider_id = provider_id
        self.failure_threshold = failure_threshold
        self.probe_successes = probe_successes
        self.base_reset_timeout_sec = base_reset_timeout_sec

        self._state = CircuitState.CLOSED
        self._lock = threading.RLock()
        self._consecutive_failures = 0
        self._consecutive_probes = 0
        self._opened_at: Optional[float] = None
        self._last_failure_reason: str = ""
        self._open_count: int = 0
        self._recovery_count: int = 0
        self._transitions: List[CircuitTransition] = []
        self._ttr_history: deque = deque(maxlen=20)

        # Observed cooldown history for adaptive reset timeout
        self._observed_cooldowns: deque = deque(maxlen=10)

    # ------------------------------------------------------------------
    # State access
    # ------------------------------------------------------------------

    def state(self) -> CircuitState:
        with self._lock:
            return self._get_state_locked()

    def _get_state_locked(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.time() >= self._open_until():
                self._transition_locked(CircuitState.HALF_OPEN, "reset_timeout_elapsed")
        return self._state

    def _open_until(self) -> float:
        if self._opened_at is None:
            return 0.0
        timeout = self._adaptive_reset_timeout()
        return self._opened_at + timeout

    def _adaptive_reset_timeout(self) -> float:
        """Use observed cooldown history to estimate reset timeout."""
        if self._observed_cooldowns:
            avg_cd = sum(self._observed_cooldowns) / len(self._observed_cooldowns)
            return max(self.base_reset_timeout_sec, avg_cd * 1.2)
        return self.base_reset_timeout_sec

    # ------------------------------------------------------------------
    # State machine transitions
    # ------------------------------------------------------------------

    def _transition_locked(self, new_state: CircuitState, reason: str):
        if new_state == self._state:
            return
        tr = CircuitTransition(self._state, new_state, reason)
        self._transitions.append(tr)
        logger.info(f"[CircuitBreaker] {self.provider_id}: {self._state.name} → {new_state.name} ({reason})")
        self._state = new_state

        if new_state == CircuitState.OPEN:
            self._opened_at = time.time()
            self._open_count += 1
            self._consecutive_probes = 0
        elif new_state == CircuitState.CLOSED:
            if self._opened_at is not None:
                ttr = time.time() - self._opened_at
                self._ttr_history.append(ttr)
                logger.info(f"[CircuitBreaker] {self.provider_id} recovered in {ttr:.1f}s")
            self._consecutive_failures = 0
            self._consecutive_probes = 0
            self._recovery_count += 1
        elif new_state == CircuitState.HALF_OPEN:
            self._consecutive_probes = 0

    def is_allowed(self) -> bool:
        """Returns True if a request should be attempted."""
        with self._lock:
            st = self._get_state_locked()
            if st == CircuitState.CLOSED:
                return True
            if st == CircuitState.HALF_OPEN:
                return True   # Allow probe
            return False  # OPEN

    def record_success(self):
        with self._lock:
            st = self._get_state_locked()
            self._consecutive_failures = 0
            if st == CircuitState.HALF_OPEN:
                self._consecutive_probes += 1
                if self._consecutive_probes >= self.probe_successes:
                    self._transition_locked(CircuitState.CLOSED, f"probe_successes={self._consecutive_probes}")
            # Closed: just reset failure count (done above)

    def record_failure(self, reason: str = "", cooldown_hint: float = 0.0):
        with self._lock:
            self._consecutive_failures += 1
            self._last_failure_reason = reason
            if cooldown_hint > 0.0:
                self._observed_cooldowns.append(cooldown_hint)
            st = self._get_state_locked()
            if st in (CircuitState.CLOSED, CircuitState.HALF_OPEN):
                if self._consecutive_failures >= self.failure_threshold:
                    self._transition_locked(
                        CircuitState.OPEN,
                        f"failures={self._consecutive_failures}, reason={reason[:80]}"
                    )

    def record_429(self, retry_after: float = 0.0):
        """429s count as failures for circuit breaker purposes."""
        self.record_failure(reason="HTTP_429", cooldown_hint=retry_after if retry_after > 0 else 60.0)

    def time_until_open(self) -> float:
        with self._lock:
            if self._state != CircuitState.OPEN:
                return 0.0
            return max(0.0, self._open_until() - time.time())

    def to_dict(self) -> dict:
        with self._lock:
            st = self._get_state_locked()
            ttrs = list(self._ttr_history)
            avg_ttr = sum(ttrs) / len(ttrs) if ttrs else 0.0
            return {
                "provider_id": self.provider_id,
                "state": st.name,
                "consecutive_failures": self._consecutive_failures,
                "failure_threshold": self.failure_threshold,
                "open_count": self._open_count,
                "recovery_count": self._recovery_count,
                "time_until_open_sec": round(self.time_until_open(), 2),
                "adaptive_reset_timeout_sec": round(self._adaptive_reset_timeout(), 2),
                "last_failure_reason": self._last_failure_reason,
                "recent_transitions": [t.to_dict() for t in self._transitions[-5:]],
                "avg_ttr_sec": round(avg_ttr, 2),
                "ttr_history": [round(t, 2) for t in ttrs],
            }


class AdaptiveCooldownScheduler:
    """
    Task 2: Tracks cooldown windows per provider using observed retry-after data.
    Improves estimates over time via exponential moving average.
    """

    def __init__(self):
        self._cooldowns: Dict[str, float] = {}        # provider_id -> cooldown_until timestamp
        self._observed: Dict[str, deque] = {}         # provider_id -> deque of observed retry delays
        self._lock = threading.Lock()
        self._events: List[dict] = []

    def _ensure(self, provider_id: str):
        if provider_id not in self._observed:
            self._observed[provider_id] = deque(maxlen=20)
            self._cooldowns[provider_id] = 0.0

    def register_429(self, provider_id: str, retry_after: float = 0.0):
        with self._lock:
            self._ensure(provider_id)
            estimated = self._estimate_cooldown(provider_id, retry_after)
            self._cooldowns[provider_id] = time.time() + estimated
            self._observed[provider_id].append(estimated)
            event = {
                "provider": provider_id,
                "cooldown_sec": round(estimated, 2),
                "retry_after_hint": retry_after,
                "cooldown_until": time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ",
                    time.gmtime(self._cooldowns[provider_id])
                ),
                "timestamp": time.time(),
            }
            self._events.append(event)
            logger.info(f"[CooldownScheduler] {provider_id} cooldown={estimated:.1f}s")
            return estimated

    def _estimate_cooldown(self, provider_id: str, retry_after: float) -> float:
        """
        Use Retry-After if provided.
        Otherwise derive from observed history (EMA).
        Adds 10% safety margin.
        """
        if retry_after > 0.0:
            return retry_after * 1.1

        obs = self._observed[provider_id]
        if obs:
            ema = obs[-1]
            for v in list(obs)[-5:]:
                ema = 0.3 * v + 0.7 * ema
            return max(10.0, ema * 1.1)

        # Default starting point
        return 60.0

    def is_in_cooldown(self, provider_id: str) -> bool:
        with self._lock:
            self._ensure(provider_id)
            return time.time() < self._cooldowns.get(provider_id, 0.0)

    def cooldown_remaining(self, provider_id: str) -> float:
        with self._lock:
            self._ensure(provider_id)
            return max(0.0, self._cooldowns.get(provider_id, 0.0) - time.time())

    def all_cooldowns(self) -> dict:
        with self._lock:
            now = time.time()
            result = {}
            for pid, until in self._cooldowns.items():
                remaining = max(0.0, until - now)
                result[pid] = {
                    "provider_id": pid,
                    "in_cooldown": remaining > 0.0,
                    "cooldown_remaining_sec": round(remaining, 2),
                    "cooldown_until_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(until)) if until else None,
                    "event_count": len(self._events),
                }
            return result

    def recent_events(self, n: int = 50) -> list:
        with self._lock:
            return list(self._events[-n:])


class CircuitBreakerRegistry:
    """Global registry for all provider circuit breakers."""

    def __init__(self):
        self._breakers: Dict[str, ProviderCircuitBreaker] = {}
        self._lock = threading.Lock()

    def get(self, provider_id: str) -> ProviderCircuitBreaker:
        with self._lock:
            if provider_id not in self._breakers:
                self._breakers[provider_id] = ProviderCircuitBreaker(provider_id)
            return self._breakers[provider_id]

    def all_states(self) -> dict:
        with self._lock:
            return {pid: cb.to_dict() for pid, cb in self._breakers.items()}

    def all_provider_ids(self):
        with self._lock:
            return list(self._breakers.keys())


# Singletons
_circuit_registry: Optional[CircuitBreakerRegistry] = None
_cooldown_scheduler: Optional[AdaptiveCooldownScheduler] = None
_cb_lock = threading.Lock()


def get_circuit_registry() -> CircuitBreakerRegistry:
    global _circuit_registry
    with _cb_lock:
        if _circuit_registry is None:
            _circuit_registry = CircuitBreakerRegistry()
        return _circuit_registry


def get_cooldown_scheduler() -> AdaptiveCooldownScheduler:
    global _cooldown_scheduler
    with _cb_lock:
        if _cooldown_scheduler is None:
            _cooldown_scheduler = AdaptiveCooldownScheduler()
        return _cooldown_scheduler
