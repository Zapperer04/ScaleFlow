from abc import ABC, abstractmethod
from typing import Optional
from backend.dto.worker import WorkerTaskDTO

class WorkerService(ABC):
    """Application Service interface for task processing orchestration."""
    @abstractmethod
    def lease_next_task(self, worker_id: str) -> Optional[WorkerTaskDTO]:
        """Lease the next available task from the queue."""
        pass

    @abstractmethod
    def complete_task(self, task_id: int) -> None:
        """Mark task execution as successfully completed."""
        pass

    @abstractmethod
    def fail_task(self, task_id: int, error_message: str) -> None:
        """Mark task execution as failed with details."""
        pass
