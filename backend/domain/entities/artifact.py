from dataclasses import dataclass
from typing import Dict, Any, Optional
from backend.domain.value_objects.artifact_id import ArtifactId
from backend.domain.value_objects.pipeline_id import PipelineId

@dataclass(frozen=True)
class Artifact:
    artifact_id: Optional[ArtifactId]
    pipeline_id: PipelineId
    task_id: Optional[int]
    artifact_type: str
    storage_uri: str
    metadata_json: Dict[str, Any]
    checksum: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact_id": self.artifact_id.to_dict() if self.artifact_id else None,
            "pipeline_id": self.pipeline_id.to_dict(),
            "task_id": self.task_id,
            "artifact_type": self.artifact_type,
            "storage_uri": self.storage_uri,
            "metadata_json": self.metadata_json,
            "checksum": self.checksum,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Artifact":
        art_id = data.get("artifact_id")
        return cls(
            artifact_id=ArtifactId.from_dict(art_id) if art_id is not None else None,
            pipeline_id=PipelineId.from_dict(data["pipeline_id"]),
            task_id=data.get("task_id"),
            artifact_type=str(data["artifact_type"]),
            storage_uri=str(data["storage_uri"]),
            metadata_json=data.get("metadata_json", {}),
            checksum=data.get("checksum"),
        )
