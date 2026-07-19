import time
import threading
from typing import Dict, Any

class ProviderMetrics:
    def __init__(self):
        self._lock = threading.Lock()
        self.pages_processed = 0
        self.total_latency = 0.0
        self.retries = 0
        self.failures = 0
        self.successes = 0
        self.token_usage = 0

    def record_success(self, pages: int, latency: float, tokens: int = 0):
        with self._lock:
            self.pages_processed += pages
            self.total_latency += latency
            self.successes += 1
            self.token_usage += tokens

    def record_failure(self, latency: float):
        with self._lock:
            self.total_latency += latency
            self.failures += 1

    def record_retry(self):
        with self._lock:
            self.retries += 1

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            avg_latency = self.total_latency / (self.successes + self.failures) if (self.successes + self.failures) > 0 else 0.0
            return {
                "pages_processed": self.pages_processed,
                "latency": avg_latency,
                "total_latency": self.total_latency,
                "retries": self.retries,
                "failures": self.failures,
                "successful_requests": self.successes,
                "token_usage": self.token_usage,
            }
