from sqlalchemy.orm import Session
from backend.repositories.unit_of_work import UnitOfWork
from backend.infrastructure.persistence.sqlalchemy.document_repository import SqlAlchemyDocumentRepository
from backend.infrastructure.persistence.sqlalchemy.artifact_repository import SqlAlchemyArtifactRepository
from backend.infrastructure.persistence.sqlalchemy.pipeline_repository import SqlAlchemyPipelineRepository
from backend.infrastructure.persistence.sqlalchemy.embedding_repository import SqlAlchemyEmbeddingRepository
from backend.infrastructure.persistence.sqlalchemy.retrieval_repository import SqlAlchemyRetrievalRepository

class SqlAlchemyUnitOfWork(UnitOfWork):
    """SQLAlchemy-backed implementation of the UnitOfWork contract."""

    def __init__(self, session: Session):
        self._session = session
        self._documents = SqlAlchemyDocumentRepository(session)
        self._artifacts = SqlAlchemyArtifactRepository(session)
        self._pipelines = SqlAlchemyPipelineRepository(session)
        self._embeddings = SqlAlchemyEmbeddingRepository(session)
        self._retrievals = SqlAlchemyRetrievalRepository(session)

    @property
    def documents(self) -> SqlAlchemyDocumentRepository:
        return self._documents

    @property
    def artifacts(self) -> SqlAlchemyArtifactRepository:
        return self._artifacts

    @property
    def pipelines(self) -> SqlAlchemyPipelineRepository:
        return self._pipelines

    @property
    def embeddings(self) -> SqlAlchemyEmbeddingRepository:
        return self._embeddings

    @property
    def retrievals(self) -> SqlAlchemyRetrievalRepository:
        return self._retrievals

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
