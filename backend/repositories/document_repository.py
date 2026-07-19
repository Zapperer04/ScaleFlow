from typing import Optional
from backend.repositories.base import Repository
from backend.domain.aggregates.document import Document
from backend.domain.value_objects.document_id import DocumentId

class DocumentRepository(Repository[Document, DocumentId]):
    """Document repository interface."""
    def get_by_filename(self, filename: str) -> Optional[Document]:
        raise NotImplementedError
