from abc import ABC, abstractmethod
from typing import List, Dict, Any

class Retriever(ABC):
    """Interface for retrievers."""
    @abstractmethod
    def retrieve(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant content/chunks based on the query."""
        pass
