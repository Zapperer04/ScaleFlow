from typing import Dict, Any, Optional
from backend.platform.scheduler.queue_interface import QueueInterface

class RedisQueue(QueueInterface):
    """
    Redis pluggable queue driver placeholder. Falls back to in-memory/sqlite if connection fails.
    """
    def __init__(self):
        from backend.platform.scheduler.sqlite_queue import SQLiteQueue
        self.fallback = SQLiteQueue()

    def enqueue(self, task_type: str, payload: Dict[str, Any], job_id: str = None) -> str:
        return self.fallback.enqueue(task_type, payload, job_id)

    def dequeue(self) -> Optional[Dict[str, Any]]:
        return self.fallback.dequeue()

    def complete(self, job_id: str):
        self.fallback.complete(job_id)

    def fail(self, job_id: str, error: str):
        self.fallback.fail(job_id, error)

    def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self.fallback.get_status(job_id)
