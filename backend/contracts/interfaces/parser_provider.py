from typing import Dict, Any
from abc import ABC, abstractmethod

class ParserProvider(ABC):
    """Interface for parser providers."""
    @abstractmethod
    def parse(self, file_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Parse document and return a dict representing ParserResponse."""
        pass
