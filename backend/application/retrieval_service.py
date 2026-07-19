from abc import ABC, abstractmethod
from typing import List
from backend.domain.entities.retrieval import Retrieval
from backend.dto.retrieval import RetrievalRequestDTO

class RetrievalService(ABC):
    """Application Service interface for orchestrating document retrieval."""
    @abstractmethod
    def retrieve_context(self, request: RetrievalRequestDTO) -> Retrieval:
        """Process retrieval request and return Domain Retrieval representation."""
        pass
