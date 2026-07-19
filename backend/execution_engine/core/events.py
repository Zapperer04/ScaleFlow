from enum import Enum
from typing import Any, Dict
from pydantic import BaseModel, Field
import time
from uuid import uuid4

class EventType(str, Enum):
    LEASE_ACQUIRED = "LEASE_ACQUIRED"
    PROVIDER_SELECTED = "PROVIDER_SELECTED"
    PROMPT_SENT = "PROMPT_SENT"
    STREAM_STARTED = "STREAM_STARTED"
    JSON_VALIDATED = "JSON_VALIDATED"
    ARTIFACT_WRITTEN = "ARTIFACT_WRITTEN"
    LEASE_RELEASED = "LEASE_RELEASED"
    JOB_FAILED = "JOB_FAILED"

class ExecutionEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: float = Field(default_factory=time.time)
    type: EventType
    trace_id: str
    job_id: str
    payload: Dict[str, Any] = Field(default_factory=dict)

class EventEmitter:
    """
    Abstract event emitter. Business logic calls this instead of logging.
    """
    @classmethod
    def emit(cls, event: ExecutionEvent):
        # MVP: just print/log for now. Later this goes to a real Event Store.
        print(f"[{event.timestamp}] {event.type.value} | Job: {event.job_id} | Trace: {event.trace_id} | Payload: {event.payload}")
