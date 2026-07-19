from typing import Optional, List
from sqlalchemy.orm import Session
from backend.repositories.embedding_repository import EmbeddingRepository
from backend.domain.entities.embedding import Embedding
from backend.domain.value_objects.chunk_id import ChunkId

class SqlAlchemyEmbeddingRepository(EmbeddingRepository):
    """SQLAlchemy/Metadata implementation of EmbeddingRepository."""

    def __init__(self, session: Session):
        self.session = session
        # Keep a local store in memory as metadata because there is no DB table for embeddings
        self._store = {}

    def save(self, entity: Embedding) -> None:
        self._store[entity.chunk_id.value] = entity

    def load(self, id: ChunkId) -> Optional[Embedding]:
        return self._store.get(id.value)

    def get_by_id(self, id: ChunkId) -> Optional[Embedding]:
        return self.load(id)

    def delete(self, id: ChunkId) -> None:
        if id.value in self._store:
            del self._store[id.value]

    def get_by_chunk_id(self, chunk_id: ChunkId) -> Optional[Embedding]:
        return self.load(chunk_id)

    def list(self) -> List[Embedding]:
        return list(self._store.values())

    def health(self) -> dict:
        return {"status": "healthy", "type": "embedding_repository"}
