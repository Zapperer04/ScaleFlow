from typing import List
from backend.repositories.base import Repository
from backend.domain.entities.artifact import Artifact
from backend.domain.value_objects.artifact_id import ArtifactId
from backend.domain.value_objects.pipeline_id import PipelineId

class ArtifactRepository(Repository[Artifact, ArtifactId]):
    """Artifact repository interface."""
    def get_by_pipeline_id(self, pipeline_id: PipelineId) -> List[Artifact]:
        raise NotImplementedError
