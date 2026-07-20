import uuid
import time
from typing import Dict, Any, Optional

class ProviderSession:
    """
    Manages request-scoped state for a single provider execution attempt.
    Tracks trace, request, timeout, retry budget, and metric telemetry.
    """
    def __init__(
        self,
        provider_id: str,
        trace_id: str,
        request_id: Optional[str] = None,
        timeout: float = 60.0,
        retry_budget: int = 3
    ):
        self.provider_id = provider_id
        self.trace_id = trace_id
        self.request_id = request_id or f"req-{uuid.uuid4()}"
        self.timeout = timeout
        self.retry_budget = retry_budget
        self.metrics: Dict[str, Any] = {
            "queue_wait_ms": 0.0,
            "lease_wait_ms": 0.0,
            "provider_wait_ms": 0.0,
            "inference_time_ms": 0.0,
            "validation_time_ms": 0.0,
            "normalization_time_ms": 0.0,
            "artifact_write_ms": 0.0,
            "total_time_ms": 0.0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_estimate": 0.0
        }
        self.start_time = time.time()
        self.failure_layer: Optional[str] = None
        self.failure_reason: Optional[str] = None

    def record_duration(self, metric_key: str, duration_sec: float):
        if metric_key in self.metrics:
            self.metrics[metric_key] = duration_sec * 1000.0

    def finalize(self):
        self.metrics["total_time_ms"] = (time.time() - self.start_time) * 1000.0

    def mark_failure(self, layer: str, reason: str):
        self.failure_layer = layer
        self.failure_reason = reason
        self.finalize()
