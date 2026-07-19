from abc import ABC, abstractmethod
from typing import Sequence, List, Optional, Dict, Any
from dataclasses import dataclass, field

@dataclass
class VectorPoint:
    id: str
    vector: List[float]
    payload: Dict[str, Any] = field(default_factory=dict)

@dataclass
class VectorQueryFilter:
    conditions: Dict[str, Any] = field(default_factory=dict)

class BaseVectorStore(ABC):
    """Abstract interface for vector database indexing and querying operations."""

    @abstractmethod
    def upsert(self, collection_name: str, points: Sequence[VectorPoint]) -> None:
        """Upsert points (vectors + payloads) into a collection."""
        pass

    @abstractmethod
    def delete(self, collection_name: str, point_ids: List[str]) -> None:
        """Delete points by their IDs from a collection."""
        pass

    @abstractmethod
    def query(
        self,
        collection_name: str,
        vector: List[float],
        limit: int = 5,
        filter: Optional[VectorQueryFilter] = None
    ) -> List[Dict[str, Any]]:
        """Query similar vectors from a collection."""
        pass

    @abstractmethod
    def batch_query(
        self,
        collection_name: str,
        vectors: List[List[float]],
        limit: int = 5
    ) -> List[List[Dict[str, Any]]]:
        """Perform batch queries for multiple vectors."""
        pass

    @abstractmethod
    def health(self) -> dict:
        """Check vector store health/liveness."""
        pass
