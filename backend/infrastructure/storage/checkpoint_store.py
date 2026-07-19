import json
from abc import ABC, abstractmethod
from typing import Dict, Any
from backend.infrastructure.storage.base_storage import BaseBinaryStorage

class BaseCheckpointStore(ABC):
    """Abstract interface for checkpoint persistence."""

    @abstractmethod
    def save_checkpoint(self, task_id: int, checkpoint_data: Dict[str, Any]) -> None:
        """Save checkpoint data for a specific task."""
        pass

    @abstractmethod
    def load_checkpoint(self, task_id: int) -> Dict[str, Any]:
        """Load checkpoint data for a specific task."""
        pass

    @abstractmethod
    def health(self) -> dict:
        """Check checkpoint store health status."""
        pass

class BinaryCheckpointStore(BaseCheckpointStore):
    """Checkpoint store that persists checkpoints as JSON files via BaseBinaryStorage."""

    def __init__(self, binary_storage: BaseBinaryStorage):
        self.binary_storage = binary_storage

    def _checkpoint_path(self, task_id: int) -> str:
        return f"checkpoints/task_{task_id}.json"

    def save_checkpoint(self, task_id: int, checkpoint_data: Dict[str, Any]) -> None:
        path = self._checkpoint_path(task_id)
        data_bytes = json.dumps(checkpoint_data).encode("utf-8")
        self.binary_storage.save_bytes(path, data_bytes)

    def load_checkpoint(self, task_id: int) -> Dict[str, Any]:
        path = self._checkpoint_path(task_id)
        try:
            data_bytes = self.binary_storage.load_bytes(path)
            return json.loads(data_bytes.decode("utf-8"))
        except FileNotFoundError:
            return {}

    def health(self) -> dict:
        storage_health = self.binary_storage.health()
        return {
            "status": storage_health.get("status", "unknown"),
            "type": "checkpoint_store",
            "storage": storage_health
        }
