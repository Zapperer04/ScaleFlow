from typing import Optional, List
from sqlalchemy.orm import Session
from backend.repositories.artifact_repository import ArtifactRepository
from backend.domain.entities.artifact import Artifact
from backend.domain.value_objects.artifact_id import ArtifactId
from backend.domain.value_objects.pipeline_id import PipelineId
from backend.models import Artifact as LegacyArtifact, ArtifactType

class SqlAlchemyArtifactRepository(ArtifactRepository):
    """SQLAlchemy implementation of ArtifactRepository wrapping the artifacts table queries."""

    def __init__(self, session: Session):
        self.session = session

    def _to_domain(self, record: LegacyArtifact) -> Artifact:
        import json
        metadata = record.metadata_json
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except Exception:
                metadata = {}
        elif metadata is None:
            metadata = {}
            
        return Artifact(
            artifact_id=ArtifactId(record.id),
            pipeline_id=PipelineId(record.pipeline_id),
            task_id=record.task_id,
            artifact_type=record.artifact_type.value if record.artifact_type else "unknown",
            storage_uri=record.storage_uri,
            metadata_json=metadata,
            checksum=record.checksum
        )

    def save(self, entity: Artifact) -> None:
        art_type = ArtifactType(entity.artifact_type)
        record = None
        if entity.artifact_id:
            record = self.session.query(LegacyArtifact).filter(LegacyArtifact.id == entity.artifact_id.value).first()
        
        if not record:
            record = LegacyArtifact(
                pipeline_id=entity.pipeline_id.value,
                task_id=entity.task_id,
                artifact_type=art_type,
                storage_uri=entity.storage_uri,
                metadata_json=entity.metadata_json,
                checksum=entity.checksum
            )
            self.session.add(record)
        else:
            record.pipeline_id = entity.pipeline_id.value
            record.task_id = entity.task_id
            record.artifact_type = art_type
            record.storage_uri = entity.storage_uri
            record.metadata_json = entity.metadata_json
            record.checksum = entity.checksum

    def load(self, id: ArtifactId) -> Optional[Artifact]:
        record = self.session.query(LegacyArtifact).filter(LegacyArtifact.id == id.value).first()
        if not record:
            return None
        return self._to_domain(record)

    def get_by_id(self, id: ArtifactId) -> Optional[Artifact]:
        return self.load(id)

    def list(self, document_id: Optional[int] = None) -> List[Artifact]:
        # If document_id is specified, in legacy we don't have direct mapping, but we might filter by pipeline or document
        # Let's list all or filter if pipeline matches
        query = self.session.query(LegacyArtifact)
        if document_id is not None:
            # Assume pipeline_id maps or find artifacts
            query = query.filter(LegacyArtifact.pipeline_id == document_id)
        records = query.all()
        return [self._to_domain(r) for r in records]

    def delete(self, id: ArtifactId) -> None:
        record = self.session.query(LegacyArtifact).filter(LegacyArtifact.id == id.value).first()
        if record:
            self.session.delete(record)

    def get_by_pipeline_id(self, pipeline_id: PipelineId) -> List[Artifact]:
        records = self.session.query(LegacyArtifact).filter(LegacyArtifact.pipeline_id == pipeline_id.value).all()
        return [self._to_domain(r) for r in records]

    def health(self) -> dict:
        try:
            self.session.execute("SELECT 1")
            return {"status": "healthy", "type": "artifact_repository"}
        except Exception as e:
            return {"status": "unhealthy", "type": "artifact_repository", "error": str(e)}
