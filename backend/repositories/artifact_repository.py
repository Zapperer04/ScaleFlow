from typing import List, Optional
from backend.repositories.base import Repository
from backend.domain.entities.artifact import Artifact
from backend.domain.value_objects.artifact_id import ArtifactId
from backend.domain.value_objects.pipeline_id import PipelineId

class ArtifactRepository(Repository[Artifact, ArtifactId]):
    """Artifact repository interface."""
    def save(self, entity: Artifact) -> None:
        raise NotImplementedError

    def load(self, id: ArtifactId) -> Optional[Artifact]:
        raise NotImplementedError

    def list(self, document_id: Optional[int] = None) -> List[Artifact]:
        raise NotImplementedError

    def delete(self, id: ArtifactId) -> None:
        raise NotImplementedError

    def get_by_pipeline_id(self, pipeline_id: PipelineId) -> List[Artifact]:
        raise NotImplementedError

