from typing import Optional, List
from backend.repositories.base import Repository
from backend.domain.entities.embedding import Embedding
from backend.domain.value_objects.chunk_id import ChunkId

class EmbeddingRepository(Repository[Embedding, ChunkId]):
    """Embedding repository interface."""
    def save(self, entity: Embedding) -> None:
        raise NotImplementedError

    def load(self, id: ChunkId) -> Optional[Embedding]:
        raise NotImplementedError

    def delete(self, id: ChunkId) -> None:
        raise NotImplementedError

    def get_by_chunk_id(self, chunk_id: ChunkId) -> Optional[Embedding]:
        raise NotImplementedError

