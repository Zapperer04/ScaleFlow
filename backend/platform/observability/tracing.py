import os
import logging
from typing import Optional

logger = logging.getLogger("platform.tracing")

class TelemetrySpan:
    def __init__(self, name: str, trace_id: str, parent_id: Optional[str] = None):
        self.name = name
        self.trace_id = trace_id
        self.parent_id = parent_id
        self.start_time = 0.0

    def __enter__(self):
        import time
        self.start_time = time.time()
        logger.info(f"[SPAN START] Name: {self.name} | TraceID: {self.trace_id} | ParentID: {self.parent_id}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        duration = time.time() - self.start_time
        status = "ERROR" if exc_type else "OK"
        logger.info(f"[SPAN END] Name: {self.name} | TraceID: {self.trace_id} | Status: {status} | Duration: {duration:.4f}s")
        return False


class TelemetryTracer:
    def __init__(self):
        # Configure file logging if not set
        from backend.platform.config.settings import settings
        os.makedirs(settings.LOGS_DIR, exist_ok=True)
        log_file = os.path.join(settings.LOGS_DIR, "traces.log")
        if not logger.handlers:
            handler = logging.FileHandler(log_file)
            formatter = logging.Formatter('%(asctime)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

    def start_span(self, name: str, trace_id: str, parent_id: Optional[str] = None) -> TelemetrySpan:
        return TelemetrySpan(name, trace_id, parent_id)
