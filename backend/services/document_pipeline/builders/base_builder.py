from abc import ABC, abstractmethod
from typing import List, Dict, Any
from services.document_pipeline.schemas import CanonicalDocument

class BaseBuilder(ABC):
    @abstractmethod
    def build(self, doc: CanonicalDocument, context: Dict[str, Any]) -> Any:
        """
        Executes the representation generation.
        context is a shared dictionary containing output from upstream builders.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        pass

    @property
    def dependencies(self) -> List[str]:
        return []
