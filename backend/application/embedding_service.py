from abc import ABC, abstractmethod
from typing import List
from backend.domain.entities.chunk import Chunk
from backend.domain.entities.embedding import Embedding

class EmbeddingService(ABC):
    """Application Service interface for orchestrating vector generation."""
    @abstractmethod
    def embed_chunks(self, chunks: List[Chunk]) -> List[Embedding]:
        """Embed a list of chunks and return domain Embeddings."""
        pass
