import os
import time
import random
import threading
import redis
import uuid
import logging
import json
from typing import Optional, Tuple, Dict, Any, Callable, Union
from email.utils import parsedate_to_datetime
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo  # Python 3.9+ standard library

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
    Extended with intelligent 429 classification, adaptive backoff state machine,
    distributed circuit breaker, adaptive batch recommendation, upload URI cache,
    enhanced metrics, and better logging.
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

    # New defaults for extended features
    DEFAULT_MIN_BATCH_SIZE = 2
    DEFAULT_MAX_BATCH_SIZE = 8
    DEFAULT_CIRCUIT_BREAKER_THRESHOLD = 5       # consecutive failures to open
    DEFAULT_CIRCUIT_BREAKER_TIMEOUT = 60.0      # seconds to wait before attempting probe (used if no explicit reset)
    DEFAULT_UPLOAD_CACHE_TTL = 86400.0          # 24 hours
    DEFAULT_MAX_FAILURE_STREAK = 10             # cap for backoff computation
    DEFAULT_SUCCESS_RECOVERY_THRESHOLD = 3      # consecutive successes to increase batch size
    DEFAULT_RESET_TIMEZONE = "America/Los_Angeles"  # for RPD reset

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
            # New local state for extended features (fallback)
            "failure_streak": 0,
            "breaker_state": "CLOSED",
            "breaker_opened_at": 0.0,
            "breaker_next_probe": 0.0,
            "breaker_probe_sent": 0,
            "last_429_classification": "UNKNOWN",
            "success_count_since_last_failure": 0,
            "last_quota_reset_time": 0.0,
            "upload_cache_hits": 0,
            "upload_cache_misses": 0,
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

        # New configuration
        self.min_batch_size = int(os.getenv("GEMINI_MIN_BATCH_SIZE", self.DEFAULT_MIN_BATCH_SIZE))
        self.max_batch_size = int(os.getenv("GEMINI_MAX_BATCH_SIZE", self.DEFAULT_MAX_BATCH_SIZE))
        self.circuit_breaker_threshold = int(os.getenv("GEMINI_CIRCUIT_BREAKER_THRESHOLD", self.DEFAULT_CIRCUIT_BREAKER_THRESHOLD))
        self.circuit_breaker_timeout = float(os.getenv("GEMINI_CIRCUIT_BREAKER_TIMEOUT", self.DEFAULT_CIRCUIT_BREAKER_TIMEOUT))
        self.upload_cache_ttl = float(os.getenv("GEMINI_UPLOAD_CACHE_TTL", self.DEFAULT_UPLOAD_CACHE_TTL))
        self.max_failure_streak = int(os.getenv("GEMINI_MAX_FAILURE_STREAK", self.DEFAULT_MAX_FAILURE_STREAK))
        self.success_recovery_threshold = int(os.getenv("GEMINI_SUCCESS_RECOVERY_THRESHOLD", self.DEFAULT_SUCCESS_RECOVERY_THRESHOLD))
        self.reset_timezone_str = os.getenv("GEMINI_RESET_TIMEZONE", self.DEFAULT_RESET_TIMEZONE)

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
            self._lua_breaker_attempt_probe = None
            self._lua_breaker_close = None
            self._lua_breaker_open = None
            self._lua_breaker_get_state = None
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

        # ---- New Lua scripts for circuit breaker ----
        try:
            # Attempt to allow a probe request.
            # Returns 1 if probe is allowed (and state transitioned), else 0.
            self._lua_breaker_attempt_probe = self.redis_client.register_script("""
                local state_key = KEYS[1]
                local opened_at_key = KEYS[2]
                local next_probe_key = KEYS[3]
                local probe_sent_key = KEYS[4]
                local now = tonumber(ARGV[1])
                local timeout = tonumber(ARGV[2])
                local state = redis.call('GET', state_key) or 'CLOSED'
                if state == 'OPEN' then
                    local next_probe = tonumber(redis.call('GET', next_probe_key) or '0')
                    if now >= next_probe then
                        -- transition to HALF_OPEN and set probe_sent
                        redis.call('SET', state_key, 'HALF_OPEN')
                        redis.call('SET', probe_sent_key, '1', 'EX', timeout)
                        return 1
                    else
                        return 0
                    end
                elseif state == 'HALF_OPEN' then
                    -- check if probe_sent exists
                    local sent = redis.call('EXISTS', probe_sent_key)
                    if sent == 0 then
                        -- no probe in flight, allow this one
                        redis.call('SET', probe_sent_key, '1', 'EX', timeout)
                        return 1
                    else
                        return 0
                    end
                else
                    -- CLOSED: no probe needed
                    return 0
                end
            """)
        except Exception as e:
            logger.error(f"Failed to register _lua_breaker_attempt_probe: {e}")
            self._lua_breaker_attempt_probe = None

        try:
            # Close the breaker: set state CLOSED, clear probe_sent, clear timestamps
            self._lua_breaker_close = self.redis_client.register_script("""
                local state_key = KEYS[1]
                local opened_at_key = KEYS[2]
                local next_probe_key = KEYS[3]
                local probe_sent_key = KEYS[4]
                redis.call('SET', state_key, 'CLOSED')
                redis.call('DEL', opened_at_key, next_probe_key, probe_sent_key)
                return 1
            """)
        except Exception as e:
            logger.error(f"Failed to register _lua_breaker_close: {e}")
            self._lua_breaker_close = None

        try:
            # Open the breaker: set state OPEN, set timestamps, clear probe_sent.
            # ARGV[1] = now, ARGV[2] = next_probe_time (absolute timestamp)
            self._lua_breaker_open = self.redis_client.register_script("""
                local state_key = KEYS[1]
                local opened_at_key = KEYS[2]
                local next_probe_key = KEYS[3]
                local probe_sent_key = KEYS[4]
                local now = tonumber(ARGV[1])
                local next_probe = tonumber(ARGV[2])
                redis.call('SET', state_key, 'OPEN')
                redis.call('SET', opened_at_key, now)
                redis.call('SET', next_probe_key, next_probe)
                redis.call('DEL', probe_sent_key)
                return 1
            """)
        except Exception as e:
            logger.error(f"Failed to register _lua_breaker_open: {e}")
            self._lua_breaker_open = None

        try:
            # Get breaker state and associated timestamps
            self._lua_breaker_get_state = self.redis_client.register_script("""
                local state_key = KEYS[1]
                local opened_at_key = KEYS[2]
                local next_probe_key = KEYS[3]
                local probe_sent_key = KEYS[4]
                local state = redis.call('GET', state_key) or 'CLOSED'
                local opened_at = tonumber(redis.call('GET', opened_at_key) or '0')
                local next_probe = tonumber(redis.call('GET', next_probe_key) or '0')
                local probe_sent = redis.call('EXISTS', probe_sent_key)
                return {state, opened_at, next_probe, probe_sent}
            """)
        except Exception as e:
            logger.error(f"Failed to register _lua_breaker_get_state: {e}")
            self._lua_breaker_get_state = None

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
        """
        Reset exponential backoff level and failure streak on a successful request,
        clear pause reason, and close circuit breaker if in HALF_OPEN or OPEN (probe succeeded).
        Also increments success counter for batch recovery.
        """
        # Reset backoff_level (legacy)
        self._set_value("backoff_level", 0)
        # Reset failure streak
        self._set_value("failure_streak", 0)
        self._incr_value("requests_sent")
        with self._metrics_lock:
            self._total_success += 1
        self._set_value("current_pause_reason", "")
        # Increment success count since last failure (for batch recovery)
        with self._local_lock:
            success_count = self._local_state.get("success_count_since_last_failure", 0) + 1
            self._local_state["success_count_since_last_failure"] = success_count
        # If we have a circuit breaker in HALF_OPEN or OPEN, close it (probe succeeded)
        self._close_circuit_breaker()

        # Log success with additional info
        batch_rec = self.get_recommended_batch_size()
        logger.info(f"Success registered. Backoff reset, failure streak 0, recommended batch size {batch_rec}.")
        logger.debug(f"Success: breaker state={self._get_breaker_state()}, batch_rec={batch_rec}")

    def register_429(self, retry_after_header: Optional[str] = None, response: Optional[Any] = None) -> float:
        """
        Registers a 429 response.
        Parses Retry-After, classifies the 429, computes adaptive backoff based on failure streak,
        updates cooldown state, updates circuit breaker, and returns the pause duration in seconds.
        """
        self._incr_value("429_count")
        with self._metrics_lock:
            self._total_failures += 1
        now = time.time()
        self._set_value("last_429_time", now)

        # 1. Classify the 429 (if response provided)
        classification = "UNKNOWN"
        reset_time = 0.0
        if response is not None:
            classification, reset_time = self.classify_429(response)
        self._set_value("last_429_classification", classification)
        if reset_time > 0:
            self._set_value("last_quota_reset_time", reset_time)

        # 2. Increment failure streak
        streak = self._incr_value("failure_streak")  # returns new value
        # Cap streak
        if streak > self.max_failure_streak:
            self._set_value("failure_streak", self.max_failure_streak)
            streak = self.max_failure_streak

        # Reset success count since last failure
        with self._local_lock:
            self._local_state["success_count_since_last_failure"] = 0

        # 3. Parse Retry-After
        retry_after = self._parse_retry_after(retry_after_header)
        logger.debug(f"Retry-After parsed: {retry_after:.1f}s")

        # 4. Determine cooldown duration
        # If classification is RPD and reset_time is known, cooldown until reset_time (or next midnight)
        cooldown_seconds = 0.0
        if classification in ("RPD_LIMIT", "RPD") and reset_time > 0:
            cooldown_seconds = max(0.0, reset_time - now)
            if cooldown_seconds > 0:
                logger.info(f"RPD limit detected, cooldown until quota reset at {reset_time} ({cooldown_seconds:.0f}s)")
        elif retry_after > 0:
            cooldown_seconds = retry_after
        else:
            # Compute adaptive backoff using failure streak
            cooldown_seconds = self._compute_backoff_from_streak(streak)
            logger.debug(f"Computed adaptive backoff for streak {streak}: {cooldown_seconds:.1f}s")

        # 5. Cooldown extension: never shorten, merge overlapping, ignore stale
        new_cooldown = now + cooldown_seconds
        updated = self._set_cooldown_atomically(new_cooldown)
        if updated:
            logger.info(f"429 cooldown extended to {new_cooldown} (duration {cooldown_seconds:.1f}s)")

        # 6. Update pause metrics
        self._incr_float("total_pause_duration", cooldown_seconds)
        if updated:
            self._set_value("last_pause_start", now)
            reason = f"429 (classification={classification}, streak={streak}, backoff={cooldown_seconds:.1f}s)"
            self._set_value("current_pause_reason", reason)
            with self._local_lock:
                self._was_in_cooldown = True
            longest = self._get_value("longest_pause", 0.0)
            if cooldown_seconds > longest:
                self._set_value("longest_pause", cooldown_seconds)

        # 7. Circuit breaker: if failure streak >= threshold, open breaker
        # For RPD, we open immediately and set next_probe to reset_time (or soon after)
        if classification in ("RPD_LIMIT", "RPD") and reset_time > 0:
            # Open breaker with next_probe = reset_time + small buffer
            self._open_circuit_breaker(reset_time)
            logger.warning(f"Circuit breaker opened due to RPD quota exhaustion, next probe at {reset_time}")
        elif streak >= self.circuit_breaker_threshold:
            self._open_circuit_breaker()
            logger.warning(f"Circuit breaker opened due to {streak} consecutive failures.")

        # 8. Log the 429 with classification, streak, backoff, etc.
        breaker_state = self._get_breaker_state()
        batch_rec = self.get_recommended_batch_size()
        logger.info(
            f"429 registered: classification={classification}, streak={streak}, "
            f"retry_after={retry_after:.1f}s, cooldown_until={new_cooldown}, "
            f"breaker_state={breaker_state}, recommended_batch_size={batch_rec}"
        )

        return cooldown_seconds

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

        # Gather breaker info
        breaker_state, opened_at, next_probe, probe_sent = self._get_breaker_state_full()

        # Gather cache stats
        cache_hits = self._get_value("upload_cache_hits", 0)
        cache_misses = self._get_value("upload_cache_misses", 0)

        return {
            "requests_sent": self._get_value("requests_sent", 0),
            "429_count": self._get_value("429_count", 0),
            "total_pause_duration": self._get_value("total_pause_duration", 0.0),
            "cooldown_remaining": round(cooldown, 1),
            "status": "PAUSED_RATE_LIMIT" if not availability else "RUNNING",
            "current_pause_reason": self._get_value("current_pause_reason", ""),
            "last_429_time": self._get_value("last_429_time", 0.0),
            "longest_pause": self._get_value("longest_pause", 0.0),
            "backoff_level": self._get_value("backoff_level", 0),  # legacy, but we keep
            "active_requests": active,
            "total_success": total_success,
            "total_failures": total_failures,
            "average_wait_seconds": 0.0,  # No longer tracked
            "max_concurrent": self.max_active,
            "min_interval": self.min_interval,
            "last_pause_end": self._get_value("last_pause_end", 0.0),
            # New metrics
            "failure_streak": self._get_value("failure_streak", 0),
            "last_429_classification": self._get_value("last_429_classification", "UNKNOWN"),
            "recommended_batch_size": self.get_recommended_batch_size(),
            "breaker_state": breaker_state,
            "breaker_opened_at": opened_at,
            "breaker_next_probe_time": next_probe,
            "breaker_probe_pending": bool(probe_sent),
            "upload_cache_hits": cache_hits,
            "upload_cache_misses": cache_misses,
            "success_count_since_last_failure": self._local_state.get("success_count_since_last_failure", 0),
            "last_quota_reset_time": self._get_value("last_quota_reset_time", 0.0),
        }

    # ----------------------------------------------------------------------
    # Public methods for non-blocking decision and lease management
    # ----------------------------------------------------------------------

    def get_decision(self) -> RateDecision:
        """
        Returns a RateDecision object indicating whether a request can proceed.
        If not allowed, the decision includes retry_after and resume_at for checkpointing.
        This method does NOT block.
        Now incorporates circuit breaker state, with proper ordering: cooldown, pacing, then breaker.
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

        # 3. Check circuit breaker
        breaker_state, opened_at, next_probe, probe_sent = self._get_breaker_state_full()

        if breaker_state == "OPEN":
            if now >= next_probe:
                # Attempt to acquire probe token
                if self._attempt_probe():
                    # We got probe token, allow request (will be treated as probe)
                    logger.info("Circuit breaker: HALF_OPEN, probe request allowed.")
                    # Do NOT return yet; we allow.
                else:
                    # Could not get probe token, another worker is probing or we are still OPEN
                    resume_at = next_probe if next_probe > now else now + 5.0
                    return RateDecision(
                        allowed=False,
                        retry_after=resume_at - now,
                        resume_at=resume_at,
                        reason="circuit_open_waiting"
                    )
            else:
                # Still OPEN, not yet time to probe
                return RateDecision(
                    allowed=False,
                    retry_after=next_probe - now,
                    resume_at=next_probe,
                    reason="circuit_open"
                )
        elif breaker_state == "HALF_OPEN":
            # Check if we can acquire probe token (only one allowed)
            if not self._attempt_probe():
                # Another probe in flight or we already have one
                return RateDecision(
                    allowed=False,
                    retry_after=5.0,
                    resume_at=now + 5.0,
                    reason="circuit_half_open_waiting"
                )
            # else we have token, proceed
            logger.info("Circuit breaker: HALF_OPEN, probe token acquired.")

        # If we reach here, either breaker is CLOSED, or we are in HALF_OPEN with probe token,
        # or we are in OPEN and we successfully acquired probe (which transitions to HALF_OPEN).
        # In all cases, request allowed.
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
        Now also rejects if circuit breaker is OPEN (to prevent any Gemini request).
        """
        # Check circuit breaker before acquiring slot (quick reject)
        breaker_state, _, _, _ = self._get_breaker_state_full()
        if breaker_state == "OPEN":
            logger.warning("Slot acquisition blocked: circuit breaker is OPEN.")
            return None
        # Note: HALF_OPEN state still allows acquisition, but get_decision will enforce probe token.
        # We let it proceed.
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
        """Returns the current exponential backoff level (legacy, but returns failure streak for compatibility)."""
        return self._get_value("failure_streak", 0)

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
    # New Public APIs for Extended Features
    # ----------------------------------------------------------------------

    @staticmethod
    def classify_429(response: Any) -> Tuple[str, float]:
        """
        Classify a 429 response into one of the categories:
        RPM_LIMIT, TPM_LIMIT, RPD_LIMIT, MODEL_CAPACITY, TRANSIENT, UNKNOWN.
        Inspects HTTP status, JSON body, error.status, error.details, Retry-After, message text.
        Returns (classification, quota_reset_time) where quota_reset_time is a Unix timestamp
        (0 if unknown) for daily quota reset.
        """
        # Default classification
        classification = "UNKNOWN"
        reset_time = 0.0
        try:
            # If response is a dict or has .json() method
            if hasattr(response, 'json'):
                data = response.json()
            elif isinstance(response, dict):
                data = response
            else:
                data = {}
        except Exception:
            data = {}

        # Helper to parse error.details
        error = data.get('error', {})
        if not isinstance(error, dict):
            error = {}
        status = error.get('status', '')
        message = error.get('message', '')
        details = error.get('details', [])
        if not isinstance(details, list):
            details = []

        # Look for QuotaFailure or ErrorInfo in details
        for detail in details:
            if not isinstance(detail, dict):
                continue
            detail_type = detail.get('@type', '')
            if 'QuotaFailure' in detail_type:
                # QuotaFailure has 'violations' list
                violations = detail.get('violations', [])
                if not isinstance(violations, list):
                    violations = []
                for v in violations:
                    subject = v.get('subject', '')
                    description = v.get('description', '')
                    combined = f"{subject} {description}".lower()
                    if 'per minute' in combined or 'rpm' in combined:
                        classification = "RPM_LIMIT"
                    elif 'per day' in combined or 'rpd' in combined:
                        classification = "RPD_LIMIT"
                        reset_time = GeminiRateManager._get_next_midnight_pacific()
                    elif 'token' in combined or 'tpm' in combined:
                        classification = "TPM_LIMIT"
                    else:
                        # If we see QuotaFailure but can't determine, treat as RPM? Better UNKNOWN
                        pass
                    break  # first violation
            elif 'ErrorInfo' in detail_type:
                # ErrorInfo has 'reason' and 'domain'
                reason = detail.get('reason', '')
                domain = detail.get('domain', '')
                combined = f"{reason} {domain}".lower()
                if 'rate_limit' in combined or 'quota' in combined:
                    if 'per minute' in combined or 'rpm' in combined:
                        classification = "RPM_LIMIT"
                    elif 'per day' in combined or 'rpd' in combined:
                        classification = "RPD_LIMIT"
                        reset_time = GeminiRateManager._get_next_midnight_pacific()
                    elif 'token' in combined or 'tpm' in combined:
                        classification = "TPM_LIMIT"
                    else:
                        # Could be general quota, assume RPM? Better UNKNOWN
                        pass
            elif 'Help' in detail_type:
                # Help links may contain quota information, but we'll ignore
                pass

        # If still UNKNOWN, fallback to status and message but do NOT default to RPM
        if classification == "UNKNOWN":
            combined = f"{status} {message}".lower()
            normalized = combined.replace('_', ' ')
            if 'rate limit' in normalized or 'quota' in normalized or 'too many requests' in normalized or 'afford' in normalized or 'balance' in normalized or 'credits' in normalized or 'billing' in normalized:
                if 'per minute' in normalized or 'rpm' in normalized or 'slow down' in normalized:
                    classification = "RPM_LIMIT"
                elif 'per day' in normalized or 'rpd' in normalized or 'daily' in normalized or 'credits' in normalized or 'billing' in normalized or 'afford' in normalized or 'balance' in normalized:
                    classification = "RPD_LIMIT"
                    reset_time = GeminiRateManager._get_next_midnight_pacific()
                elif 'token' in normalized or 'tpm' in normalized:
                    classification = "TPM_LIMIT"
                else:
                    classification = "RPM_LIMIT"
            elif 'capacity' in normalized or 'overloaded' in normalized:
                classification = "MODEL_CAPACITY"
            elif 'retry' in normalized or 'temporary' in normalized or 'transient' in normalized:
                classification = "TRANSIENT"

        # Do NOT default to RPM; leave UNKNOWN if not matched
        return classification, reset_time

    @staticmethod
    def _get_next_midnight_pacific() -> float:
        """
        Returns Unix timestamp of next midnight (00:00) Pacific time.
        Uses zoneinfo (Python 3.9+ standard library).
        """
        tz_str = os.getenv("GEMINI_RESET_TIMEZONE", "America/Los_Angeles")
        try:
            tz = ZoneInfo(tz_str)
            now = datetime.now(tz)
            midnight = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=tz)
            if now >= midnight:
                midnight += timedelta(days=1)
            return midnight.timestamp()
        except Exception as e:
            logger.warning(f"Failed to compute midnight for {tz_str}: {e}. Falling back to UTC+24h.")
            return time.time() + 86400

    def get_recommended_batch_size(self) -> int:
        """
        Dynamically recommend a batch size based on failure streak and recent success count.
        Returns an integer between min_batch_size and max_batch_size.
        """
        streak = self._get_value("failure_streak", 0)
        success_since_last_failure = self._local_state.get("success_count_since_last_failure", 0)

        # Start with max
        batch = self.max_batch_size

        # Reduce based on streak
        if streak >= 5:
            batch = self.min_batch_size
        elif streak >= 3:
            batch = max(self.min_batch_size, int(self.max_batch_size * 0.5))
        elif streak >= 1:
            batch = max(self.min_batch_size, int(self.max_batch_size * 0.75))

        # Increase based on successive successes after a failure
        if success_since_last_failure >= self.success_recovery_threshold:
            # Gradually increase
            increment = min(2, success_since_last_failure // self.success_recovery_threshold)
            batch = min(self.max_batch_size, batch + increment)

        # Ensure within bounds
        return max(self.min_batch_size, min(self.max_batch_size, batch))

    # ---- Upload URI Cache ----
    def cache_upload(self, pdf_hash: str, file_uri: str, ttl_seconds: Optional[float] = None,
                     model: Optional[str] = None, prompt_hash: Optional[str] = None,
                     system_prompt_hash: Optional[str] = None,
                     generation_config_hash: Optional[str] = None,
                     page_start: Optional[int] = None,
                     page_end: Optional[int] = None) -> bool:
        """
        Cache the uploaded file URI for a given PDF hash and optional context.
        Returns True if stored successfully.
        """
        if ttl_seconds is None:
            ttl_seconds = self.upload_cache_ttl
        # Build cache key including optional context
        key_parts = [pdf_hash]
        if page_start is not None and page_end is not None:
            key_parts.append(f"pages:{page_start}-{page_end}")
        if model:
            key_parts.append(f"model:{model}")
        if prompt_hash:
            key_parts.append(f"prompt:{prompt_hash}")
        if system_prompt_hash:
            key_parts.append(f"system:{system_prompt_hash}")
        if generation_config_hash:
            key_parts.append(f"gencfg:{generation_config_hash}")
        cache_key = "_".join(key_parts)
        key = self._get_key(f"upload_cache:{cache_key}")

        data = {
            "uri": file_uri,
            "timestamp": time.time(),
            "expiration": time.time() + ttl_seconds
        }
        try:
            if self._ensure_redis():
                self.redis_client.setex(key, int(ttl_seconds), json.dumps(data))
                return True
            else:
                # local fallback
                with self._local_lock:
                    self._local_state[f"upload_cache_{cache_key}"] = data
                return True
        except Exception as e:
            logger.error(f"Failed to cache upload for {cache_key}: {e}")
            return False

    def lookup_upload(self, pdf_hash: str, model: Optional[str] = None,
                      prompt_hash: Optional[str] = None,
                      system_prompt_hash: Optional[str] = None,
                      generation_config_hash: Optional[str] = None,
                      page_start: Optional[int] = None,
                      page_end: Optional[int] = None) -> Optional[str]:
        """
        Look up a cached file URI for a given PDF hash and optional context.
        Returns the URI if found and not expired, else None.
        Also updates cache hit/miss metrics.
        """
        key_parts = [pdf_hash]
        if page_start is not None and page_end is not None:
            key_parts.append(f"pages:{page_start}-{page_end}")
        if model:
            key_parts.append(f"model:{model}")
        if prompt_hash:
            key_parts.append(f"prompt:{prompt_hash}")
        if system_prompt_hash:
            key_parts.append(f"system:{system_prompt_hash}")
        if generation_config_hash:
            key_parts.append(f"gencfg:{generation_config_hash}")
        cache_key = "_".join(key_parts)
        key = self._get_key(f"upload_cache:{cache_key}")

        try:
            if self._ensure_redis():
                raw = self.redis_client.get(key)
                if raw:
                    data = json.loads(raw)
                    if data.get("expiration", 0) > time.time():
                        self._incr_value("upload_cache_hits", 1)
                        return data.get("uri")
                    else:
                        # expired, delete
                        self.redis_client.delete(key)
                        self._incr_value("upload_cache_misses", 1)
                        return None
                else:
                    self._incr_value("upload_cache_misses", 1)
                    return None
            else:
                # local fallback
                with self._local_lock:
                    data = self._local_state.get(f"upload_cache_{cache_key}")
                    if data and data.get("expiration", 0) > time.time():
                        self._incr_value("upload_cache_hits", 1)
                        return data.get("uri")
                    else:
                        self._incr_value("upload_cache_misses", 1)
                        return None
        except Exception as e:
            logger.error(f"Failed to lookup upload for {cache_key}: {e}")
            return None

    def invalidate_upload(self, pdf_hash: str, model: Optional[str] = None,
                          prompt_hash: Optional[str] = None,
                          system_prompt_hash: Optional[str] = None,
                          generation_config_hash: Optional[str] = None) -> bool:
        """
        Invalidate the cached upload for a given PDF hash and optional context.
        Returns True if removed.
        """
        key_parts = [pdf_hash]
        if model:
            key_parts.append(f"model:{model}")
        if prompt_hash:
            key_parts.append(f"prompt:{prompt_hash}")
        if system_prompt_hash:
            key_parts.append(f"system:{system_prompt_hash}")
        if generation_config_hash:
            key_parts.append(f"gencfg:{generation_config_hash}")
        cache_key = "_".join(key_parts)
        key = self._get_key(f"upload_cache:{cache_key}")

        try:
            if self._ensure_redis():
                self.redis_client.delete(key)
                return True
            else:
                with self._local_lock:
                    if f"upload_cache_{cache_key}" in self._local_state:
                        del self._local_state[f"upload_cache_{cache_key}"]
                return True
        except Exception as e:
            logger.error(f"Failed to invalidate upload for {cache_key}: {e}")
            return False

    # ----------------------------------------------------------------------
    # Internal helper methods for extended features
    # ----------------------------------------------------------------------

    def _compute_backoff_from_streak(self, streak: int) -> float:
        """
        Compute exponential backoff based on failure streak.
        Uses base_backoff * (multiplier ** (streak-1)) with full jitter.
        Capped at max_backoff.
        """
        if streak <= 0:
            return 0.0
        base = self.base_backoff * (self.backoff_multiplier ** (streak - 1))
        jitter = random.uniform(0.5, 2.0)
        backoff = min(self.max_backoff, base * jitter)
        return max(0.0, backoff)

    def _get_breaker_state_full(self) -> Tuple[str, float, float, bool]:
        """Returns (state, opened_at, next_probe, probe_sent_bool)."""
        if self._ensure_redis() and self._lua_breaker_get_state is not None:
            try:
                keys = [
                    self._get_key("breaker_state"),
                    self._get_key("breaker_opened_at"),
                    self._get_key("breaker_next_probe"),
                    self._get_key("breaker_probe_sent")
                ]
                result = self._lua_breaker_get_state(keys=keys)
                state = result[0]
                opened_at = float(result[1])
                next_probe = float(result[2])
                probe_sent = int(result[3]) == 1
                return state, opened_at, next_probe, probe_sent
            except Exception:
                self._load_lua_scripts()
                if self._lua_breaker_get_state is not None:
                    try:
                        keys = [
                            self._get_key("breaker_state"),
                            self._get_key("breaker_opened_at"),
                            self._get_key("breaker_next_probe"),
                            self._get_key("breaker_probe_sent")
                        ]
                        result = self._lua_breaker_get_state(keys=keys)
                        state = result[0]
                        opened_at = float(result[1])
                        next_probe = float(result[2])
                        probe_sent = int(result[3]) == 1
                        return state, opened_at, next_probe, probe_sent
                    except Exception:
                        pass
        # Fallback to local
        with self._local_lock:
            state = self._local_state.get("breaker_state", "CLOSED")
            opened_at = self._local_state.get("breaker_opened_at", 0.0)
            next_probe = self._local_state.get("breaker_next_probe", 0.0)
            probe_sent = self._local_state.get("breaker_probe_sent", 0) == 1
            return state, opened_at, next_probe, probe_sent

    def _get_breaker_state(self) -> str:
        state, _, _, _ = self._get_breaker_state_full()
        return state

    def _attempt_probe(self) -> bool:
        """
        Attempt to acquire a probe token for circuit breaker.
        Returns True if this request is allowed as a probe.
        Uses Lua script for atomicity.
        """
        if self._ensure_redis() and self._lua_breaker_attempt_probe is not None:
            try:
                keys = [
                    self._get_key("breaker_state"),
                    self._get_key("breaker_opened_at"),
                    self._get_key("breaker_next_probe"),
                    self._get_key("breaker_probe_sent")
                ]
                args = [str(time.time()), str(self.circuit_breaker_timeout)]
                result = self._lua_breaker_attempt_probe(keys=keys, args=args)
                if int(result) == 1:
                    return True
                else:
                    return False
            except Exception:
                self._load_lua_scripts()
                if self._lua_breaker_attempt_probe is not None:
                    try:
                        keys = [
                            self._get_key("breaker_state"),
                            self._get_key("breaker_opened_at"),
                            self._get_key("breaker_next_probe"),
                            self._get_key("breaker_probe_sent")
                        ]
                        args = [str(time.time()), str(self.circuit_breaker_timeout)]
                        result = self._lua_breaker_attempt_probe(keys=keys, args=args)
                        if int(result) == 1:
                            return True
                        else:
                            return False
                    except Exception as e:
                        logger.error(f"Error in _attempt_probe: {e}")
        # Fallback: local logic with locking
        with self._local_lock:
            state = self._local_state.get("breaker_state", "CLOSED")
            if state == "OPEN":
                next_probe = self._local_state.get("breaker_next_probe", 0.0)
                if time.time() >= next_probe:
                    self._local_state["breaker_state"] = "HALF_OPEN"
                    self._local_state["breaker_probe_sent"] = 1
                    return True
                else:
                    return False
            elif state == "HALF_OPEN":
                if self._local_state.get("breaker_probe_sent", 0) == 0:
                    self._local_state["breaker_probe_sent"] = 1
                    return True
                else:
                    return False
            else:
                return False

    def _open_circuit_breaker(self, next_probe_time: Optional[float] = None):
        """
        Open the circuit breaker: set state OPEN, timestamps, clear probe_sent.
        If next_probe_time is provided, use it as the time when probe is allowed.
        Otherwise, use now + circuit_breaker_timeout.
        """
        now = time.time()
        if next_probe_time is None:
            next_probe_time = now + self.circuit_breaker_timeout
        else:
            # Ensure next_probe_time is in the future
            next_probe_time = max(next_probe_time, now + 1.0)

        if self._ensure_redis() and self._lua_breaker_open is not None:
            try:
                keys = [
                    self._get_key("breaker_state"),
                    self._get_key("breaker_opened_at"),
                    self._get_key("breaker_next_probe"),
                    self._get_key("breaker_probe_sent")
                ]
                args = [str(now), str(next_probe_time)]
                self._lua_breaker_open(keys=keys, args=args)
                return
            except Exception:
                self._load_lua_scripts()
                if self._lua_breaker_open is not None:
                    try:
                        keys = [
                            self._get_key("breaker_state"),
                            self._get_key("breaker_opened_at"),
                            self._get_key("breaker_next_probe"),
                            self._get_key("breaker_probe_sent")
                        ]
                        args = [str(now), str(next_probe_time)]
                        self._lua_breaker_open(keys=keys, args=args)
                        return
                    except Exception as e:
                        logger.error(f"Error opening breaker via Lua: {e}")
        # Fallback local
        with self._local_lock:
            self._local_state["breaker_state"] = "OPEN"
            self._local_state["breaker_opened_at"] = now
            self._local_state["breaker_next_probe"] = next_probe_time
            self._local_state["breaker_probe_sent"] = 0

    def _close_circuit_breaker(self):
        """Close the circuit breaker: set state CLOSED, clear timestamps and probe_sent."""
        if self._ensure_redis() and self._lua_breaker_close is not None:
            try:
                keys = [
                    self._get_key("breaker_state"),
                    self._get_key("breaker_opened_at"),
                    self._get_key("breaker_next_probe"),
                    self._get_key("breaker_probe_sent")
                ]
                self._lua_breaker_close(keys=keys)
                return
            except Exception:
                self._load_lua_scripts()
                if self._lua_breaker_close is not None:
                    try:
                        keys = [
                            self._get_key("breaker_state"),
                            self._get_key("breaker_opened_at"),
                            self._get_key("breaker_next_probe"),
                            self._get_key("breaker_probe_sent")
                        ]
                        self._lua_breaker_close(keys=keys)
                        return
                    except Exception as e:
                        logger.error(f"Error closing breaker via Lua: {e}")
        # Fallback local
        with self._local_lock:
            self._local_state["breaker_state"] = "CLOSED"
            self._local_state["breaker_opened_at"] = 0.0
            self._local_state["breaker_next_probe"] = 0.0
            self._local_state["breaker_probe_sent"] = 0

    # ----------------------------------------------------------------------
    # Internal helper methods (existing)
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