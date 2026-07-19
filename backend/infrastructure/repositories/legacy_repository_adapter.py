from typing import Any, Dict
from backend.domain.aggregates.document import Document
from backend.domain.value_objects.document_id import DocumentId
from backend.domain.aggregates.pipeline import Pipeline
from backend.domain.value_objects.pipeline_id import PipelineId
from backend.domain.entities.artifact import Artifact
from backend.domain.value_objects.artifact_id import ArtifactId
from backend.models import FileRecord, Pipeline as LegacyPipeline, Artifact as LegacyArtifact

class LegacyRepositoryAdapter:
    """Adapter to translate between legacy SQLAlchemy ORM models and clean Domain Models."""

    @staticmethod
    def file_record_to_document(record: FileRecord) -> Document:
        return Document(
            document_id=DocumentId(record.id),
            filename=record.original_filename,
            pages=[],
            chunks=[],
            graph=None,
            metadata=record.to_dict(),
            artifacts=[]
        )

    @staticmethod
    def pipeline_to_domain(record: LegacyPipeline) -> Pipeline:
        from backend.adapters.pipeline_adapter import PipelineAdapter
        return PipelineAdapter.legacy_to_domain(record)

    @staticmethod
    def artifact_to_domain(record: LegacyArtifact) -> Artifact:
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
