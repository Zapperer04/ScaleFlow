from abc import ABC, abstractmethod
from backend.repositories.document_repository import DocumentRepository
from backend.repositories.artifact_repository import ArtifactRepository
from backend.repositories.pipeline_repository import PipelineRepository
from backend.repositories.embedding_repository import EmbeddingRepository
from backend.repositories.retrieval_repository import RetrievalRepository

class UnitOfWork(ABC):
    """Abstract Unit of Work pattern interface for transactional boundary management."""

    @property
    @abstractmethod
    def documents(self) -> DocumentRepository:
        pass

    @property
    @abstractmethod
    def artifacts(self) -> ArtifactRepository:
        pass

    @property
    @abstractmethod
    def pipelines(self) -> PipelineRepository:
        pass

    @property
    @abstractmethod
    def embeddings(self) -> EmbeddingRepository:
        pass

    @property
    @abstractmethod
    def retrievals(self) -> RetrievalRepository:
        pass

    @abstractmethod
    def commit(self) -> None:
        pass

    @abstractmethod
    def rollback(self) -> None:
        pass
