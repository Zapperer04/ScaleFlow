from abc import ABC, abstractmethod
from typing import List
from backend.domain.entities.embedding import Embedding
from backend.domain.entities.chunk import Chunk

class IndexingService(ABC):
    """Application Service interface for orchestrating document indexing."""
    @abstractmethod
    def index_document(self, pipeline_id: int, chunks: List[Chunk], embeddings: List[Embedding]) -> None:
        """Indexes chunks and embeddings into the storage systems."""
        pass
