import os
import time
import random
import threading
import redis
import uuid
import logging
from typing import Optional, Tuple, Dict, Any, Callable
from email.utils import parsedate_to_datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Custom exception to signal that the rate manager requires a pause
class RateLimitPauseRequired(Exception):
    """Raised when the rate manager determines that the caller must pause and resume later."""
    def __init__(self, resume_at: float, reason: str = "", retry_after: float = 0.0):
        self.resume_at = resume_at
        self.reason = reason
        self.retry_after = retry_after
        super().__init__(f"Rate limit pause required until {resume_at} (reason: {reason})")

@dataclass
class RateDecision:
    """
    Represents the rate manager's decision for a request.
    - allowed: True if request can proceed immediately.
    - retry_after: Seconds to wait (0 if allowed).
    - resume_at: Unix timestamp when the request can be retried (0 if allowed).
    - reason: Human-readable reason (e.g., "cooldown", "pacing", "quota").
    """
    allowed: bool
    retry_after: float
    resume_at: float
    reason: str = ""

class GeminiRateManager:
    """
    Central Gemini Rate Manager.
    Coordinates rate limiting, cooldown, provider-aware exponential backoff with jitter,
    global request pacing, and distributed concurrency control with lease-based slots.
    Uses Redis for shared state across workers; falls back to local thread-safe state.
    This manager does NOT block; it returns decisions or raises RateLimitPauseRequired.
    """
    _instance = None
    _lock = threading.Lock()

    # Default constants
    DEFAULT_MIN_INTERVAL_SECONDS = 0.5          # Minimum time between requests
    DEFAULT_MAX_ACTIVE_REQUESTS = 10            # Default, override via env/config
    DEFAULT_BASE_BACKOFF_SECONDS = 5.0          # Base backoff for 429
    DEFAULT_MAX_BACKOFF_SECONDS = 300.0         # Cap backoff
    DEFAULT_BACKOFF_MULTIPLIER = 1.5            # Multiplier per level
    DEFAULT_RETRY_AFTER_FALLBACK = 60.0         # Fallback if Retry-After parsing fails
    DEFAULT_LEASE_TTL_SECONDS = 300.0           # TTL for active request slots (5 minutes)
    MAX_RETRY_AFTER = 3600.0                    # Cap for Retry-After to prevent infinite pauses

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(GeminiRateManager, cls).__new__(cls, *args, **kwargs)
                cls._instance._init_manager()
            return cls._instance

    def _init_manager(self):
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("REDIS_PORT", 6379))
        self._redis_client = None
        self._redis_lock = threading.Lock()
        self._last_reconnect_attempt = 0
        self._reconnect_backoff = 1.0
        self._local_state = {
            "cooldown_until": 0.0,
            "backoff_level": 0,
            "requests_sent": 0,
            "429_count": 0,
            "total_pause_duration": 0.0,
            "last_pause_start": 0.0,
            "last_pause_end": 0.0,
            "current_pause_reason": "",
            "last_429_time": 0.0,
            "longest_pause": 0.0,
        }
        self._local_lock = threading.Lock()
        self._metrics_lock = threading.Lock()   # For counters like _total_success, _total_failures
        self._shutdown_requested = False
        self._active_slot_ids = set()  # Slots owned by this process
        self._was_in_cooldown = False   # Track cooldown exit to set last_pause_end (protected by _local_lock)

        # Configuration
        self.min_interval = float(os.getenv("GEMINI_MIN_INTERVAL_SECONDS", self.DEFAULT_MIN_INTERVAL_SECONDS))
        # Read max active from environment or config module if available, fallback to default
        max_active_env = os.getenv("GEMINI_MAX_ACTIVE_REQUESTS")
        if max_active_env is not None:
            self.max_active = int(max_active_env)
        else:
            # Try to import config and use its value if present
            try:
                import sys
                sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                import config
                self.max_active = getattr(config, "GEMINI_MAX_ACTIVE_REQUESTS", self.DEFAULT_MAX_ACTIVE_REQUESTS)
            except (ImportError, AttributeError):
                self.max_active = self.DEFAULT_MAX_ACTIVE_REQUESTS
        self.base_backoff = float(os.getenv("GEMINI_BASE_BACKOFF_SECONDS", self.DEFAULT_BASE_BACKOFF_SECONDS))
        self.max_backoff = float(os.getenv("GEMINI_MAX_BACKOFF_SECONDS", self.DEFAULT_MAX_BACKOFF_SECONDS))
        self.backoff_multiplier = float(os.getenv("GEMINI_BACKOFF_MULTIPLIER", self.DEFAULT_BACKOFF_MULTIPLIER))
        self.retry_after_fallback = float(os.getenv("GEMINI_RETRY_AFTER_FALLBACK", self.DEFAULT_RETRY_AFTER_FALLBACK))
        self.lease_ttl = float(os.getenv("GEMINI_LEASE_TTL_SECONDS", self.DEFAULT_LEASE_TTL_SECONDS))

        # Statistics for metrics
        self._total_success = 0
        self._total_failures = 0

        # Initialize Redis client if possible
        self._connect_redis()
        # Load Lua scripts
        self._load_lua_scripts()

    def _connect_redis(self) -> bool:
        """Establish or re-establish Redis connection with exponential backoff and jitter."""
        now = time.time()
        if now - self._last_reconnect_attempt < self._reconnect_backoff:
            # Throttle reconnection attempts
            return False
        self._last_reconnect_attempt = now
        with self._redis_lock:
            try:
                if self._redis_client is None:
                    self._redis_client = redis.Redis(
                        host=self.redis_host,
                        port=self.redis_port,
                        decode_responses=True,
                        socket_timeout=2,
                        socket_connect_timeout=2
                    )
                # Ping to verify
                self._redis_client.ping()
                # Reload scripts in case Redis restarted
                self._load_lua_scripts()
                logger.info("Redis connected successfully.")
                self._reconnect_backoff = 1.0  # reset backoff on success
                return True
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}. Falling back to local mode.")
                self._redis_client = None
                # Exponential backoff with jitter to avoid thundering herd
                self._reconnect_backoff = min(30.0, self._reconnect_backoff * 2) * (0.8 + 0.4 * random.random())
                return False

    @property
    def redis_client(self):
        """Lazy reconnect if disconnected, with throttling."""
        if self._redis_client is None and not self._shutdown_requested:
            self._connect_redis()
        return self._redis_client

    def _ensure_redis(self) -> bool:
        """Ensure Redis is available; return True if connected."""
        return self.redis_client is not None

    def _load_lua_scripts(self):
        """Load Lua scripts for atomic operations if Redis is available."""
        if not self._ensure_redis():
            self._lua_set_cooldown = None
            self._lua_pace_request = None
            self._lua_acquire_slot = None
            self._lua_release_slot = None
            self._lua_validate_slot = None
            self._lua_renew_slot = None
            return

        try:
            # Script to atomically set cooldown_until only if new value is larger
            self._lua_set_cooldown = self.redis_client.register_script("""
                local key = KEYS[1]
                local new_val = tonumber(ARGV[1])
                local current = redis.call('GET', key)
                if not current or tonumber(current) < new_val then
                    redis.call('SET', key, new_val)
                    return 1
                end
                return 0
            """)
        except Exception as e:
            logger.error(f"Failed to register _lua_set_cooldown: {e}")
            self._lua_set_cooldown = None

        try:
            # Script for pacing: stores next_allowed_time = max(next_allowed_time, now + interval)
            self._lua_pace_request = self.redis_client.register_script("""
                local key = KEYS[1]
                local now = tonumber(ARGV[1])
                local interval = tonumber(ARGV[2])
                local next_allowed = redis.call('GET', key)
                if not next_allowed then
                    redis.call('SET', key, now + interval)
                    return 0
                end
                next_allowed = tonumber(next_allowed)
                if now >= next_allowed then
                    redis.call('SET', key, now + interval)
                    return 0
                else
                    return next_allowed - now
                end
            """)
        except Exception as e:
            logger.error(f"Failed to register _lua_pace_request: {e}")
            self._lua_pace_request = None

        try:
            # Script to acquire a concurrency slot with lease TTL
            self._lua_acquire_slot = self.redis_client.register_script("""
                local slots_key = KEYS[1]
                local max_active = tonumber(ARGV[1])
                local ttl = tonumber(ARGV[2])
                local now = tonumber(ARGV[3])
                local slot_id = ARGV[4]
                redis.call('ZREMRANGEBYSCORE', slots_key, '-inf', now)
                local count = redis.call('ZCARD', slots_key)
                if count < max_active then
                    redis.call('ZADD', slots_key, now + ttl, slot_id)
                    return 1
                else
                    return 0
                end
            """)
        except Exception as e:
            logger.error(f"Failed to register _lua_acquire_slot: {e}")
            self._lua_acquire_slot = None

        try:
            # Script to release a slot
            self._lua_release_slot = self.redis_client.register_script("""
                local slots_key = KEYS[1]
                local slot_id = ARGV[1]
                return redis.call('ZREM', slots_key, slot_id)
            """)
        except Exception as e:
            logger.error(f"Failed to register _lua_release_slot: {e}")
            self._lua_release_slot = None

        try:
            # Script to validate a slot
            self._lua_validate_slot = self.redis_client.register_script("""
                local slots_key = KEYS[1]
                local slot_id = ARGV[1]
                local now = tonumber(ARGV[2])
                redis.call('ZREMRANGEBYSCORE', slots_key, '-inf', now)
                local score = redis.call('ZSCORE', slots_key, slot_id)
                if score then
                    return 1
                else
                    return 0
                end
            """)
        except Exception as e:
            logger.error(f"Failed to register _lua_validate_slot: {e}")
            self._lua_validate_slot = None

        try:
            # Script to renew a slot
            self._lua_renew_slot = self.redis_client.register_script("""
                local slots_key = KEYS[1]
                local slot_id = ARGV[1]
                local now = tonumber(ARGV[2])
                local ttl = tonumber(ARGV[3])
                local score = redis.call('ZSCORE', slots_key, slot_id)
                if score then
                    redis.call('ZADD', slots_key, now + ttl, slot_id)
                    return 1
                else
                    return 0
                end
            """)
        except Exception as e:
            logger.error(f"Failed to register _lua_renew_slot: {e}")
            self._lua_renew_slot = None

        logger.debug("Lua scripts loaded (or failed) successfully.")

    # ----------------------------------------------------------------------
    # Internal helpers for Redis operations with fallback
    # ----------------------------------------------------------------------
    def _get_key(self, name: str) -> str:
        return f"gemini:rate_manager:{name}"

    def _get_value(self, name: str, default: Any) -> Any:
        if self._ensure_redis():
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
        if self._ensure_redis():
            try:
                key = self._get_key(name)
                self.redis_client.set(key, str(value), ex=expire_seconds)
                return
            except Exception:
                pass
        with self._local_lock:
            self._local_state[name] = value

    def _incr_value(self, name: str, amount: int = 1) -> int:
        if self._ensure_redis():
            try:
                key = self._get_key(name)
                return int(self.redis_client.incrby(key, amount))
            except Exception:
                pass
        with self._local_lock:
            self._local_state[name] = self._local_state.get(name, 0) + amount
            return self._local_state[name]

    def _incr_float(self, name: str, amount: float) -> float:
        if self._ensure_redis():
            try:
                key = self._get_key(name)
                return float(self.redis_client.incrbyfloat(key, amount))
            except Exception:
                pass
        with self._local_lock:
            self._local_state[name] = self._local_state.get(name, 0.0) + amount
            return self._local_state[name]

    def _set_cooldown_atomically(self, new_cooldown: float) -> bool:
        """Atomically set cooldown_until only if new value is larger."""
        if self._ensure_redis() and self._lua_set_cooldown is not None:
            try:
                key = self._get_key("cooldown_until")
                result = self._lua_set_cooldown(keys=[key], args=[str(new_cooldown)])
                if int(result) == 1:
                    logger.debug(f"Cooldown extended to {new_cooldown} (Redis)")
                return int(result) == 1
            except Exception:
                self._load_lua_scripts()
                if self._lua_set_cooldown is not None:
                    try:
                        result = self._lua_set_cooldown(keys=[key], args=[str(new_cooldown)])
                        if int(result) == 1:
                            logger.debug(f"Cooldown extended to {new_cooldown} (Redis after reload)")
                        return int(result) == 1
                    except Exception:
                        logger.warning("Failed to set cooldown in Redis; falling back to local.")
        # Fallback to local with lock
        with self._local_lock:
            current = self._local_state.get("cooldown_until", 0.0)
            if new_cooldown > current:
                self._local_state["cooldown_until"] = new_cooldown
                logger.debug(f"Cooldown extended to {new_cooldown} (local)")
                return True
            return False

    def _pace_request_atomically(self, now: float) -> float:
        """Atomically reserve next allowed time; returns wait seconds (0 if ready)."""
        if self._ensure_redis() and self._lua_pace_request is not None:
            try:
                key = self._get_key("next_allowed_time")
                remaining = self._lua_pace_request(keys=[key], args=[str(now), str(self.min_interval)])
                remaining = float(remaining)
                if remaining > 0:
                    logger.debug(f"Pacing: need to wait {remaining:.2f}s (Redis)")
                else:
                    logger.debug("Pacing: allowed (Redis)")
                return remaining
            except Exception:
                self._load_lua_scripts()
                if self._lua_pace_request is not None:
                    try:
                        remaining = self._lua_pace_request(keys=[key], args=[str(now), str(self.min_interval)])
                        remaining = float(remaining)
                        if remaining > 0:
                            logger.debug(f"Pacing: need to wait {remaining:.2f}s (Redis after reload)")
                        else:
                            logger.debug("Pacing: allowed (Redis after reload)")
                        return remaining
                    except Exception:
                        logger.warning("Failed to pace request in Redis; falling back to local.")
        # Local fallback with lock
        with self._local_lock:
            last = self._local_state.get("last_request_timestamp", 0.0)
            next_allowed = last + self.min_interval
            if now >= next_allowed:
                self._local_state["last_request_timestamp"] = now
                logger.debug("Pacing: allowed (local)")
                return 0.0
            else:
                remaining = next_allowed - now
                logger.debug(f"Pacing: need to wait {remaining:.2f}s (local)")
                return remaining

    def _acquire_slot_atomically(self) -> Optional[str]:
        """
        Atomically acquire a concurrency slot with lease.
        Returns slot_id (str) if acquired, else None.
        """
        if not self._ensure_redis() or self._lua_acquire_slot is None:
            # Fallback: when Redis is unavailable, allow only ONE concurrent request globally per worker.
            # This is a conservative fallback; note that it is process-local, so multiple workers
            # may each run one request concurrently, which could exceed the intended global limit.
            logger.warning("Redis unavailable or slot script not loaded; concurrency control is local with max_active=1 to avoid over-subscription.")
            with self._local_lock:
                active = self._local_state.get("active_requests", 0)
                if active < 1:
                    self._local_state["active_requests"] = active + 1
                    logger.debug("Slot acquired locally (fallback mode, max 1)")
                    return "local_slot"
                logger.debug("Slot acquisition failed (local fallback): max active reached")
                return None

        slot_id = str(uuid.uuid4())
        try:
            key = self._get_key("active_slots")
            result = self._lua_acquire_slot(
                keys=[key],
                args=[str(self.max_active), str(self.lease_ttl), str(time.time()), slot_id]
            )
            if int(result) == 1:
                with self._local_lock:
                    self._active_slot_ids.add(slot_id)
                logger.debug(f"Slot acquired: {slot_id}")
                return slot_id
            logger.debug("Slot acquisition failed: max active reached")
            return None
        except Exception:
            self._load_lua_scripts()
            if self._lua_acquire_slot is not None:
                try:
                    result = self._lua_acquire_slot(
                        keys=[key],
                        args=[str(self.max_active), str(self.lease_ttl), str(time.time()), slot_id]
                    )
                    if int(result) == 1:
                        with self._local_lock:
                            self._active_slot_ids.add(slot_id)
                        logger.debug(f"Slot acquired: {slot_id} (after reload)")
                        return slot_id
                    logger.debug("Slot acquisition failed: max active reached (after reload)")
                    return None
                except Exception as e:
                    logger.error(f"Error acquiring slot: {e}. Falling back to local.")
            # Final fallback: local with limit 1
            with self._local_lock:
                active = self._local_state.get("active_requests", 0)
                if active < 1:
                    self._local_state["active_requests"] = active + 1
                    logger.debug("Slot acquired locally (fallback, limit 1)")
                    return "local_slot"
                logger.debug("Slot acquisition failed (local fallback): max active reached")
                return None

    def _release_slot_atomically(self, slot_id: str):
        """Release a slot by slot_id."""
        if slot_id == "local_slot":
            with self._local_lock:
                active = self._local_state.get("active_requests", 0)
                if active > 0:
                    self._local_state["active_requests"] = active - 1
                    logger.debug("Slot released locally")
            return

        if not self._ensure_redis() or self._lua_release_slot is None:
            with self._local_lock:
                if slot_id in self._active_slot_ids:
                    self._active_slot_ids.remove(slot_id)
                    active = self._local_state.get("active_requests", 0)
                    if active > 0:
                        self._local_state["active_requests"] = active - 1
                        logger.debug(f"Slot {slot_id} released locally (fallback)")
            return

        try:
            key = self._get_key("active_slots")
            self._lua_release_slot(keys=[key], args=[slot_id])
            logger.debug(f"Slot {slot_id} released")
        except Exception:
            self._load_lua_scripts()
            if self._lua_release_slot is not None:
                try:
                    self._lua_release_slot(keys=[key], args=[slot_id])
                    logger.debug(f"Slot {slot_id} released (after reload)")
                except Exception as e:
                    logger.error(f"Error releasing slot: {e}")
        # Remove from local set regardless
        with self._local_lock:
            self._active_slot_ids.discard(slot_id)

    def _validate_slot_atomically(self, slot_id: str) -> bool:
        """Check if a slot is still active and not expired."""
        if slot_id == "local_slot":
            with self._local_lock:
                return slot_id in self._active_slot_ids or self._local_state.get("active_requests", 0) > 0

        if not self._ensure_redis() or self._lua_validate_slot is None:
            with self._local_lock:
                return slot_id in self._active_slot_ids

        try:
            key = self._get_key("active_slots")
            result = self._lua_validate_slot(keys=[key], args=[slot_id, str(time.time())])
            valid = int(result) == 1
            if valid:
                logger.debug(f"Slot {slot_id} validated")
            else:
                logger.debug(f"Slot {slot_id} invalid/expired")
            return valid
        except Exception:
            self._load_lua_scripts()
            if self._lua_validate_slot is not None:
                try:
                    result = self._lua_validate_slot(keys=[key], args=[slot_id, str(time.time())])
                    valid = int(result) == 1
                    if valid:
                        logger.debug(f"Slot {slot_id} validated (after reload)")
                    else:
                        logger.debug(f"Slot {slot_id} invalid/expired (after reload)")
                    return valid
                except Exception as e:
                    logger.error(f"Error validating slot: {e}")
                    return False
            return False

    def _renew_slot_atomically(self, slot_id: str) -> bool:
        """Renew a slot's lease, extending its TTL."""
        if slot_id == "local_slot":
            return True

        if not self._ensure_redis() or self._lua_renew_slot is None:
            with self._local_lock:
                return slot_id in self._active_slot_ids

        try:
            key = self._get_key("active_slots")
            result = self._lua_renew_slot(keys=[key], args=[slot_id, str(time.time()), str(self.lease_ttl)])
            return int(result) == 1
        except Exception:
            self._load_lua_scripts()
            if self._lua_renew_slot is not None:
                try:
                    result = self._lua_renew_slot(keys=[key], args=[slot_id, str(time.time()), str(self.lease_ttl)])
                    return int(result) == 1
                except Exception as e:
                    logger.error(f"Error renewing slot: {e}")
                    return False
            return False

    def _emit_trace(self, trace_fn: Optional[Callable], message: str):
        if trace_fn:
            trace_fn(message)

    # ----------------------------------------------------------------------
    # Public API (preserved and extended)
    # ----------------------------------------------------------------------

    def check_availability(self) -> Tuple[bool, float]:
        """
        Returns (is_available, cooldown_remaining_seconds)
        Also updates last_pause_end when cooldown ends.
        """
        cooldown_until = self._get_value("cooldown_until", 0.0)
        now = time.time()
        if now < cooldown_until:
            remaining = max(0.0, cooldown_until - now)
            logger.debug(f"check_availability: cooldown active, remaining {remaining:.1f}s")
            with self._local_lock:
                self._was_in_cooldown = True
            return False, remaining
        else:
            with self._local_lock:
                if self._was_in_cooldown:
                    # The cooldown ended at cooldown_until
                    self._set_value("last_pause_end", cooldown_until)
                    self._was_in_cooldown = False
                    logger.debug(f"Cooldown ended at {cooldown_until}")
            logger.debug("check_availability: available")
            return True, 0.0

    def register_success(self):
        """Reset exponential backoff level on a successful request and clear pause reason."""
        self._set_value("backoff_level", 0)
        self._incr_value("requests_sent")
        with self._metrics_lock:
            self._total_success += 1
        self._set_value("current_pause_reason", "")
        logger.debug("Success registered, backoff reset and pause reason cleared.")

    def register_429(self, retry_after_header: Optional[str] = None) -> float:
        """
        Registers a 429 response.
        Parses Retry-After, computes backoff with Full Jitter, updates cooldown state,
        and returns the pause duration in seconds.
        """
        self._incr_value("429_count")
        with self._metrics_lock:
            self._total_failures += 1
        now = time.time()
        self._set_value("last_429_time", now)

        # 1. Parse Retry-After
        retry_after = self._parse_retry_after(retry_after_header)
        logger.debug(f"Retry-After parsed: {retry_after:.1f}s")

        # 2. If Retry-After not given or invalid, compute exponential backoff with Full Jitter
        if retry_after <= 0.0:
            backoff_level = self._incr_value("backoff_level")
            retry_after = self._compute_backoff(backoff_level)
            logger.debug(f"Computed exponential backoff level {backoff_level}: {retry_after:.1f}s")

        # 3. Cooldown extension: never shorten, merge overlapping, ignore stale
        new_cooldown = now + retry_after
        updated = self._set_cooldown_atomically(new_cooldown)
        if updated:
            logger.info(f"429 cooldown extended to {new_cooldown} (duration {retry_after:.1f}s)")

        # 4. Update pause metrics
        self._incr_float("total_pause_duration", retry_after)
        if updated:
            self._set_value("last_pause_start", now)
            self._set_value("current_pause_reason", f"429 (backoff {retry_after:.1f}s)")
            with self._local_lock:
                self._was_in_cooldown = True
            longest = self._get_value("longest_pause", 0.0)
            if retry_after > longest:
                self._set_value("longest_pause", retry_after)

        return retry_after

    def wait_if_needed(self, trace_fn: Optional[Callable] = None) -> None:
        """
        Checks if a wait is needed and raises RateLimitPauseRequired if so.
        This method does NOT block; it returns immediately or raises an exception.
        """
        decision = self.get_decision()
        if not decision.allowed:
            self._emit_trace(trace_fn, f"[Rate Manager] Pause required: {decision.reason} until {decision.resume_at}")
            raise RateLimitPauseRequired(
                resume_at=decision.resume_at,
                reason=decision.reason,
                retry_after=decision.retry_after
            )
        self._emit_trace(trace_fn, "[Rate Manager] Request allowed")

    def get_metrics(self) -> Dict[str, Any]:
        availability, cooldown = self.check_availability()
        active = 0
        if self._ensure_redis():
            try:
                key = self._get_key("active_slots")
                active = self.redis_client.zcard(key)
            except Exception:
                pass
        if active == 0:
            with self._local_lock:
                active = self._local_state.get("active_requests", 0)

        with self._metrics_lock:
            total_success = self._total_success
            total_failures = self._total_failures

        return {
            "requests_sent": self._get_value("requests_sent", 0),
            "429_count": self._get_value("429_count", 0),
            "total_pause_duration": self._get_value("total_pause_duration", 0.0),
            "cooldown_remaining": round(cooldown, 1),
            "status": "PAUSED_RATE_LIMIT" if not availability else "RUNNING",
            "current_pause_reason": self._get_value("current_pause_reason", ""),
            "last_429_time": self._get_value("last_429_time", 0.0),
            "longest_pause": self._get_value("longest_pause", 0.0),
            "backoff_level": self._get_value("backoff_level", 0),
            "active_requests": active,
            "total_success": total_success,
            "total_failures": total_failures,
            "average_wait_seconds": 0.0,  # No longer tracked
            "max_concurrent": self.max_active,
            "min_interval": self.min_interval,
            "last_pause_end": self._get_value("last_pause_end", 0.0),
        }

    # ----------------------------------------------------------------------
    # Public methods for non-blocking decision and lease management
    # ----------------------------------------------------------------------

    def get_decision(self) -> RateDecision:
        """
        Returns a RateDecision object indicating whether a request can proceed.
        If not allowed, the decision includes retry_after and resume_at for checkpointing.
        This method does NOT block.
        """
        now = time.time()
        logger.debug("get_decision called")

        # 1. Check cooldown
        available, cooldown_remaining = self.check_availability()
        if not available:
            resume_at = self._get_value("cooldown_until", 0.0)
            logger.info(f"Decision: NOT allowed - cooldown active until {resume_at}")
            return RateDecision(
                allowed=False,
                retry_after=cooldown_remaining,
                resume_at=resume_at,
                reason="cooldown"
            )

        # 2. Check global pacing (min interval)
        pace_remaining = self._pace_request_atomically(now)
        if pace_remaining > 0:
            resume_at = now + pace_remaining
            logger.info(f"Decision: NOT allowed - pacing wait {pace_remaining:.2f}s")
            return RateDecision(
                allowed=False,
                retry_after=pace_remaining,
                resume_at=resume_at,
                reason="pacing"
            )

        logger.debug("Decision: allowed")
        return RateDecision(
            allowed=True,
            retry_after=0.0,
            resume_at=0.0,
            reason="allowed"
        )

    def wait_for_turn(self, trace_fn: Optional[Callable] = None) -> None:
        """
        Checks if it's this process's turn to make a request.
        This method does NOT block; it raises RateLimitPauseRequired if not allowed.
        """
        decision = self.get_decision()
        if not decision.allowed:
            self._emit_trace(trace_fn, f"[Rate Manager] Pacing wait required: {decision.reason} until {decision.resume_at}")
            raise RateLimitPauseRequired(
                resume_at=decision.resume_at,
                reason=decision.reason,
                retry_after=decision.retry_after
            )
        self._emit_trace(trace_fn, "[Rate Manager] Turn granted")

    def acquire_request_slot(self, timeout: Optional[float] = None) -> Optional[str]:
        """
        Acquires a concurrency slot (lease) if available.
        Returns slot_id (str) on success, None if no slot available.
        This method does NOT block; it tries once and returns immediately.
        The caller must release the slot using release_request_slot(slot_id).
        """
        return self._acquire_slot_atomically()

    def release_request_slot(self, slot_id: str):
        """Releases a previously acquired concurrency slot."""
        self._release_slot_atomically(slot_id)

    def validate_slot(self, slot_id: str) -> bool:
        """Check if a slot (lease) is still active and not expired."""
        return self._validate_slot_atomically(slot_id)

    def renew_slot(self, slot_id: str) -> bool:
        """Renew a slot's lease, extending its TTL. Returns True if renewed successfully."""
        return self._renew_slot_atomically(slot_id)

    def is_rate_limited(self) -> bool:
        """Returns True if currently in cooldown."""
        available, _ = self.check_availability()
        return not available

    def cooldown_remaining(self) -> float:
        """Returns remaining cooldown seconds (0 if not in cooldown)."""
        _, remaining = self.check_availability()
        return remaining

    def current_backoff_level(self) -> int:
        """Returns the current exponential backoff level."""
        return self._get_value("backoff_level", 0)

    def get_resume_at(self) -> float:
        """Returns the Unix timestamp when cooldown ends (0 if not in cooldown)."""
        cooldown_until = self._get_value("cooldown_until", 0.0)
        now = time.time()
        if now < cooldown_until:
            return cooldown_until
        return 0.0

    def shutdown(self):
        """Gracefully shutdown the manager, releasing all active slots and Redis connection."""
        self._shutdown_requested = True
        # Release any slots held by this process
        with self._local_lock:
            slot_ids = list(self._active_slot_ids)
            for sid in slot_ids:
                self._release_slot_atomically(sid)
            self._active_slot_ids.clear()
        # Close Redis connection
        if self._redis_client:
            try:
                self._redis_client.close()
                logger.info("Redis connection closed.")
            except Exception:
                pass

    # ----------------------------------------------------------------------
    # Context manager support for slots
    # ----------------------------------------------------------------------
    class SlotContext:
        """Context manager for automatic slot release."""
        def __init__(self, manager, slot_id):
            self.manager = manager
            self.slot_id = slot_id

        def __enter__(self):
            return self.slot_id

        def __exit__(self, exc_type, exc_val, exc_tb):
            if self.slot_id is not None:
                self.manager.release_request_slot(self.slot_id)

    def slot_context(self):
        """
        Returns a context manager that acquires a slot and releases it automatically.
        Usage:
            with rate_manager.slot_context() as slot_id:
                if slot_id is not None:
                    # do work
        """
        slot_id = self.acquire_request_slot()
        return self.SlotContext(self, slot_id)

    # ----------------------------------------------------------------------
    # Internal helper methods
    # ----------------------------------------------------------------------

    def _parse_retry_after(self, header: Optional[str]) -> float:
        """Parse Retry-After header, supporting integer seconds and HTTP-date."""
        if not header:
            return -1.0
        header = str(header).strip()
        # Try parsing as integer seconds
        try:
            val = float(header)
            if val < 0:
                return -1.0
            if val > self.MAX_RETRY_AFTER:
                logger.warning(f"Retry-After {val}s exceeds max {self.MAX_RETRY_AFTER}s, capping.")
                return self.MAX_RETRY_AFTER
            return val
        except ValueError:
            pass
        # Try parsing as HTTP-date
        try:
            dt = parsedate_to_datetime(header)
            val = max(0.0, dt.timestamp() - time.time())
            if val > self.MAX_RETRY_AFTER:
                logger.warning(f"Retry-After {val}s exceeds max {self.MAX_RETRY_AFTER}s, capping.")
                return self.MAX_RETRY_AFTER
            return val
        except Exception:
            pass
        # Fallback
        return self.retry_after_fallback

    def _compute_backoff(self, level: int) -> float:
        """
        Compute exponential backoff with provider-aware jitter.
        Returns a float between 0 and max_backoff.
        """
        base = self.base_backoff * (self.backoff_multiplier ** (level - 1))
        jitter = random.uniform(0.5, 2.0)
        backoff = min(self.max_backoff, base * jitter)
        if backoff < 0:
            backoff = 0.0
        logger.debug(f"Backoff computed: level={level}, base={base}, jitter={jitter:.2f}, actual={backoff:.2f}")
        return backoff