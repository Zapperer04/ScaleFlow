from typing import Optional
from backend.repositories.base import Repository
from backend.domain.aggregates.document import Document
from backend.domain.value_objects.document_id import DocumentId

class DocumentRepository(Repository[Document, DocumentId]):
    """Document repository interface."""
    def save(self, entity: Document) -> None:
        raise NotImplementedError

    def get(self, id: DocumentId) -> Optional[Document]:
        raise NotImplementedError

    def update(self, entity: Document) -> None:
        raise NotImplementedError

    def delete(self, id: DocumentId) -> None:
        raise NotImplementedError

    def exists(self, id: DocumentId) -> bool:
        raise NotImplementedError

    def get_by_filename(self, filename: str) -> Optional[Document]:
        raise NotImplementedError

