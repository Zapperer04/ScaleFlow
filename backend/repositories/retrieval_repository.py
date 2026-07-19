from typing import List, Optional
from backend.repositories.base import Repository
from backend.domain.entities.retrieval import Retrieval

class RetrievalRepository(Repository[Retrieval, str]):
    """Retrieval repository interface using query string as key."""
    def save(self, entity: Retrieval) -> None:
        raise NotImplementedError

    def load(self, id: str) -> Optional[Retrieval]:
        raise NotImplementedError

    def delete(self, id: str) -> None:
        raise NotImplementedError

    def get_by_query(self, query: str) -> List[Retrieval]:
        raise NotImplementedError

