from abc import ABC, abstractmethod
from typing import BinaryIO

class StorageProvider(ABC):
    """Interface for storage providers."""
    @abstractmethod
    def read(self, uri: str) -> bytes:
        """Read a file/object from the storage URI."""
        pass

    @abstractmethod
    def write(self, uri: str, data: bytes) -> None:
        """Write a file/object to the storage URI."""
        pass

    @abstractmethod
    def delete(self, uri: str) -> None:
        """Delete a file/object from the storage URI."""
        pass

    @abstractmethod
    def exists(self, uri: str) -> bool:
        """Check if a file/object exists at the storage URI."""
        pass
