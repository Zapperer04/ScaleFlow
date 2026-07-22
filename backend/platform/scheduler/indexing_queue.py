from typing import Dict, Any, Optional
from backend.platform.config.settings import settings
from backend.platform.scheduler.queue_interface import QueueInterface

class IndexingQueue(QueueInterface):
    def __init__(self):
        backend = settings.QUEUE_BACKEND
        if backend == "sqlite":
            from backend.platform.scheduler.sqlite_queue import SQLiteQueue
            self.queue = SQLiteQueue()
        elif backend == "redis":
            from backend.platform.scheduler.redis_queue import RedisQueue
            self.queue = RedisQueue()
        else:
            from backend.platform.scheduler.memory_queue import MemoryQueue
            self.queue = MemoryQueue()

    def enqueue(self, task_type: str, payload: Dict[str, Any], job_id: str = None) -> str:
        return self.queue.enqueue(task_type, payload, job_id)

    def dequeue(self) -> Optional[Dict[str, Any]]:
        return self.queue.dequeue()

    def complete(self, job_id: str):
        self.queue.complete(job_id)

    def fail(self, job_id: str, error: str):
        self.queue.fail(job_id, error)

    def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self.queue.get_status(job_id)
