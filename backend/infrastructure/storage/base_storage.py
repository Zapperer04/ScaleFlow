from abc import ABC, abstractmethod

class BaseBinaryStorage(ABC):
    """Abstract interface for raw binary/blob persistence (filesystem, S3, memory, etc.)."""

    @abstractmethod
    def save_bytes(self, path: str, data: bytes) -> None:
        """Save raw bytes to the storage location."""
        pass

    @abstractmethod
    def load_bytes(self, path: str) -> bytes:
        """Load raw bytes from the storage location."""
        pass

    @abstractmethod
    def delete(self, path: str) -> None:
        """Delete raw bytes at the storage location."""
        pass

    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check if raw bytes exist at the storage location."""
        pass

    @abstractmethod
    def health(self) -> dict:
        """Check the health status of the storage provider."""
        pass
