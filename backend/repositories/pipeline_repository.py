from typing import Optional
from backend.repositories.base import Repository
from backend.domain.aggregates.pipeline import Pipeline
from backend.domain.value_objects.pipeline_id import PipelineId
from backend.domain.states import PipelineState

class PipelineRepository(Repository[Pipeline, PipelineId]):
    """Pipeline repository interface."""
    def get_by_state(self, state: PipelineState) -> Optional[Pipeline]:
        raise NotImplementedError
