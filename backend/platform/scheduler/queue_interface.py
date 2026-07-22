from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class QueueInterface(ABC):
    @abstractmethod
    def enqueue(self, task_type: str, payload: Dict[str, Any], job_id: str = None) -> str:
        """
        Enqueues a task and returns job_id.
        """
        pass

    @abstractmethod
    def dequeue(self) -> Optional[Dict[str, Any]]:
        """
        Pulls a task to execute. Returns dict containing job_id, task_type, payload.
        """
        pass

    @abstractmethod
    def complete(self, job_id: str):
        """
        Mark task as successfully completed.
        """
        pass

    @abstractmethod
    def fail(self, job_id: str, error: str):
        """
        Mark task as failed.
        """
        pass

    @abstractmethod
    def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve current status, attempts, error details.
        """
        pass
