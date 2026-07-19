from typing import Optional, List
from sqlalchemy.orm import Session
from backend.repositories.document_repository import DocumentRepository
from backend.domain.aggregates.document import Document
from backend.domain.value_objects.document_id import DocumentId
from backend.models import FileRecord, FileStatus

class SqlAlchemyDocumentRepository(DocumentRepository):
    """SQLAlchemy implementation of DocumentRepository wrapping FileRecord queries."""

    def __init__(self, session: Session):
        self.session = session

    def save(self, entity: Document) -> None:
        # Check if it already exists
        record = self.session.query(FileRecord).filter(FileRecord.id == entity.document_id.value).first()
        if not record:
            record = FileRecord(
                id=entity.document_id.value,
                original_filename=entity.filename,
                file_type=entity.metadata.get("file_type", "unknown"),
                storage_uri=entity.metadata.get("storage_uri", ""),
                size_bytes=entity.metadata.get("size_bytes", 0),
                status=FileStatus(entity.metadata.get("status", "uploaded")),
                pipeline_id=entity.metadata.get("pipeline_id")
            )
            self.session.add(record)
        else:
            record.original_filename = entity.filename
            record.file_type = entity.metadata.get("file_type", record.file_type)
            record.storage_uri = entity.metadata.get("storage_uri", record.storage_uri)
            record.size_bytes = entity.metadata.get("size_bytes", record.size_bytes)
            record.status = FileStatus(entity.metadata.get("status", record.status.value))
            record.pipeline_id = entity.metadata.get("pipeline_id", record.pipeline_id)

    def get(self, id: DocumentId) -> Optional[Document]:
        record = self.session.query(FileRecord).filter(FileRecord.id == id.value).first()
        if not record:
            return None
        return Document(
            document_id=DocumentId(record.id),
            filename=record.original_filename,
            pages=[],
            chunks=[],
            graph=None,
            metadata=record.to_dict(),
            artifacts=[]
        )

    def get_by_id(self, id: DocumentId) -> Optional[Document]:
        return self.get(id)

    def update(self, entity: Document) -> None:
        self.save(entity)

    def delete(self, id: DocumentId) -> None:
        record = self.session.query(FileRecord).filter(FileRecord.id == id.value).first()
        if record:
            self.session.delete(record)

    def exists(self, id: DocumentId) -> bool:
        return self.session.query(FileRecord).filter(FileRecord.id == id.value).count() > 0

    def get_by_filename(self, filename: str) -> Optional[Document]:
        record = self.session.query(FileRecord).filter(FileRecord.original_filename == filename).first()
        if not record:
            return None
        return Document(
            document_id=DocumentId(record.id),
            filename=record.original_filename,
            pages=[],
            chunks=[],
            graph=None,
            metadata=record.to_dict(),
            artifacts=[]
        )

    def list(self) -> List[Document]:
        records = self.session.query(FileRecord).all()
        return [
            Document(
                document_id=DocumentId(r.id),
                filename=r.original_filename,
                pages=[],
                chunks=[],
                graph=None,
                metadata=r.to_dict(),
                artifacts=[]
            ) for r in records
        ]

    def health(self) -> dict:
        try:
            self.session.execute("SELECT 1")
            return {"status": "healthy", "type": "document_repository"}
        except Exception as e:
            return {"status": "unhealthy", "type": "document_repository", "error": str(e)}
