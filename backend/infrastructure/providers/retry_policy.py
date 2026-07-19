import time
import logging
from typing import Callable, Any, Type, Tuple

logger = logging.getLogger(__name__)

class RetryPolicy:
    def __init__(
        self,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        initial_delay: float = 1.0,
        exceptions_to_retry: Tuple[Type[Exception], ...] = (Exception,),
    ):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.initial_delay = initial_delay
        self.exceptions_to_retry = exceptions_to_retry

    def execute(self, func: Callable[[], Any], on_retry_cb: Callable[[], None] = None) -> Any:
        delay = self.initial_delay
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                return func()
            except Exception as e:
                # If it's a RateLimitPauseRequired, do not retry; bubble it up
                if e.__class__.__name__ == "RateLimitPauseRequired":
                    raise e

                if not isinstance(e, self.exceptions_to_retry):
                    raise e

                last_exception = e
                if attempt < self.max_retries:
                    if on_retry_cb:
                        on_retry_cb()
                    logger.warning(f"Error executing function: {e}. Retrying in {delay}s...")
                    time.sleep(delay)
                    delay *= self.backoff_factor
                else:
                    logger.error(f"Max retries ({self.max_retries}) exhausted. Final error: {e}")
                    raise e
        if last_exception:
            raise last_exception
