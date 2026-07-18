from abc import ABC, abstractmethod
from backend.domain.aggregates.document import Document

class ParsingService(ABC):
    """Application Service interface for orchestrating document parsing."""
    @abstractmethod
    def parse_document(self, file_path: str) -> Document:
        """Parse document and return Domain model representation."""
        pass
