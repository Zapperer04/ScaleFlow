from typing import TypeVar, Generic, List, Optional

T = TypeVar("T")
ID = TypeVar("ID")

class Repository(Generic[T, ID]):
    """Abstract base repository contract."""
    def get_by_id(self, id: ID) -> Optional[T]:
        raise NotImplementedError

    def list(self) -> List[T]:
        raise NotImplementedError

    def save(self, entity: T) -> None:
        raise NotImplementedError

    def delete(self, id: ID) -> None:
        raise NotImplementedError
