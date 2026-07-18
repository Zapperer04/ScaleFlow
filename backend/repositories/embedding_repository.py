from typing import Optional, List
from backend.repositories.base import Repository
from backend.domain.entities.embedding import Embedding
from backend.domain.value_objects.chunk_id import ChunkId

class EmbeddingRepository(Repository[Embedding, ChunkId]):
    """Embedding repository interface."""
    def get_by_chunk_id(self, chunk_id: ChunkId) -> Optional[Embedding]:
        raise NotImplementedError
    
    def find_nearest(self, vector: List[float], limit: int = 5) -> List[Embedding]:
        raise NotImplementedError
