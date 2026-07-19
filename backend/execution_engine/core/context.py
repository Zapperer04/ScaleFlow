from typing import Optional
import logging
from execution_engine.core.job import JobSpec
from execution_engine.core.events import EventEmitter, ExecutionEvent, EventType

class ExecutionContext:
    def __init__(
        self,
        job: JobSpec,
        trace_id: str,
        provider_id: Optional[str] = None,
        lease_id: Optional[str] = None,
        attempt: int = 1
    ):
        self.job = job
        self.trace_id = trace_id
        self.provider_id = provider_id
        self.lease_id = lease_id
        self.attempt = attempt
        self.logger = logging.getLogger(f"ExecutionEngine.{job.id}")

    def emit(self, event_type: EventType, payload: dict = None):
        if payload is None:
            payload = {}
        event = ExecutionEvent(
            type=event_type,
            trace_id=self.trace_id,
            job_id=self.job.id,
            payload=payload
        )
        EventEmitter.emit(event)
