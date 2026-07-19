from typing import Optional
from backend.repositories.base import Repository
from backend.domain.aggregates.pipeline import Pipeline
from backend.domain.value_objects.pipeline_id import PipelineId
from backend.domain.states import PipelineState

class PipelineRepository(Repository[Pipeline, PipelineId]):
    """Pipeline repository interface."""
    def create(self, entity: Pipeline) -> None:
        raise NotImplementedError

    def update_state(self, pipeline_id: PipelineId, state: PipelineState) -> None:
        raise NotImplementedError

    def resume(self, pipeline_id: PipelineId) -> None:
        raise NotImplementedError

    def fail(self, pipeline_id: PipelineId, error_message: str) -> None:
        raise NotImplementedError

    def get_by_state(self, state: PipelineState) -> Optional[Pipeline]:
        raise NotImplementedError

