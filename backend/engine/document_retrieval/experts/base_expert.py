from abc import ABC, abstractmethod
from typing import List
from engine.document_retrieval.evidence import Evidence
from engine.document_retrieval.query_understanding import QueryUnderstanding

class BaseExpert(ABC):
    @abstractmethod
    def retrieve(self, qu: QueryUnderstanding, doc_id: str, store) -> List[Evidence]:
        """
        Executes query retrieval and returns lightweight Evidence objects.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass
