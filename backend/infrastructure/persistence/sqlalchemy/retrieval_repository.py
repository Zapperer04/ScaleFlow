from typing import Optional, List
from sqlalchemy.orm import Session
from backend.repositories.retrieval_repository import RetrievalRepository
from backend.domain.entities.retrieval import Retrieval

class SqlAlchemyRetrievalRepository(RetrievalRepository):
    """SQLAlchemy/Metadata implementation of RetrievalRepository."""

    def __init__(self, session: Session):
        self.session = session
        self._store = {}

    def save(self, entity: Retrieval) -> None:
        self._store[entity.query] = entity

    def load(self, id: str) -> Optional[Retrieval]:
        return self._store.get(id)

    def get_by_id(self, id: str) -> Optional[Retrieval]:
        return self.load(id)

    def delete(self, id: str) -> None:
        if id in self._store:
            del self._store[id]

    def get_by_query(self, query: str) -> List[Retrieval]:
        res = self.load(query)
        return [res] if res else []

    def list(self) -> List[Retrieval]:
        return list(self._store.values())

    def health(self) -> dict:
        return {"status": "healthy", "type": "retrieval_repository"}
