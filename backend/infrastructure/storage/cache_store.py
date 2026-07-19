from abc import ABC, abstractmethod
from typing import Any, Optional

class BaseCacheStore(ABC):
    """Abstract interface for caching mechanism."""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Retrieve key from cache."""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set key in cache with optional TTL."""
        pass

    @abstractmethod
    def invalidate(self, key: str) -> None:
        """Remove key from cache."""
        pass

    @abstractmethod
    def health(self) -> dict:
        """Check cache service health."""
        pass
