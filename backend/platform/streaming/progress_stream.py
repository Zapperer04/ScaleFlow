import time
from typing import Dict, Any, Callable
from backend.platform.streaming.events import PlatformEvent, EVENT_PAGE_PARSED

class ProgressTracker:
    def __init__(self, document_id: str, callback: Callable[[PlatformEvent], None] = None):
        self.document_id = document_id
        self.callback = callback
        self.start_time = time.time()

    def update_progress(self, event_type: str, step_details: str = "", percentage: float = 0.0):
        data = {
            "document_id": self.document_id,
            "step": step_details,
            "percentage": percentage,
            "elapsed_seconds": round(time.time() - self.start_time, 2)
        }
        event = PlatformEvent(event_type=event_type, data=data)
        if self.callback:
            self.callback(event)
        return event
        
    def get_trace_fn(self) -> Callable[[str], None]:
        # Connects engine process_document's trace_fn parameter to stream events
        def trace(message: str):
            # Parse layout / graph details dynamically from trace log
            step = "indexing"
            pct = 50.0
            if "Parsing" in message:
                step = "parsing"
                pct = 15.0
            elif "builder" in message or "Builder" in message:
                step = "representation_building"
                pct = 60.0
            elif "graph" in message or "Graph" in message:
                step = "graph_generation"
                pct = 80.0
                
            self.update_progress(
                event_type=EVENT_PAGE_PARSED,
                step_details=message,
                percentage=pct
            )
        return trace
