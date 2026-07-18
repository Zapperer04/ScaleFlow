from typing import List, Dict, Any
from abc import ABC, abstractmethod

class EmbeddingProvider(ABC):
    """Interface for embedding providers."""
    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding vector for a single text chunk."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embedding vectors for a batch of text chunks."""
        pass
