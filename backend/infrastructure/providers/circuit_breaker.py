import time
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)

class CircuitBreakerOpenException(Exception):
    pass

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = "CLOSED"  # CLOSED, OPEN, HALF-OPEN
        self.failure_count = 0
        self.last_failure_time = 0.0

    def execute(self, func: Callable[[], Any]) -> Any:
        self._check_state()
        try:
            result = func()
            self._on_success()
            return result
        except Exception as e:
            if e.__class__.__name__ == "RateLimitPauseRequired":
                # Rate limiting is not a provider failure for circuit breaking purposes
                raise e
            self._on_failure()
            raise e

    def _check_state(self):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                logger.info("CircuitBreaker transition to HALF-OPEN")
                self.state = "HALF-OPEN"
            else:
                raise CircuitBreakerOpenException("Circuit breaker is OPEN. Failing fast.")

    def _on_success(self):
        if self.state in ("OPEN", "HALF-OPEN"):
            logger.info("CircuitBreaker transition to CLOSED")
        self.state = "CLOSED"
        self.failure_count = 0

    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            logger.warning(f"CircuitBreaker failure threshold ({self.failure_threshold}) reached. Transition to OPEN")
            self.state = "OPEN"
