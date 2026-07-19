from typing import List
from backend.repositories.base import Repository
from backend.domain.entities.retrieval import Retrieval

class RetrievalRepository(Repository[Retrieval, str]):
    """Retrieval repository interface using query string as key."""
    def get_by_query(self, query: str) -> List[Retrieval]:
        raise NotImplementedError
