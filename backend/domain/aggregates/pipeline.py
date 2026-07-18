from dataclasses import dataclass, field
from typing import List, Dict, Any
from backend.domain.value_objects.pipeline_id import PipelineId
from backend.domain.states import PipelineState, validate_transition
from backend.domain.entities.artifact import Artifact

@dataclass(frozen=True)
class Pipeline:
    pipeline_id: PipelineId
    name: str
    state: PipelineState
    tasks: List[Dict[str, Any]] = field(default_factory=list)
    artifacts: List[Artifact] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)

    def transition_to(self, new_state: PipelineState) -> "Pipeline":
        validate_transition(self.state, new_state)
        return Pipeline(
            pipeline_id=self.pipeline_id,
            name=self.name,
            state=new_state,
            tasks=self.tasks,
            artifacts=self.artifacts,
            events=self.events,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id.to_dict(),
            "name": self.name,
            "state": self.state.value,
            "tasks": self.tasks,
            "artifacts": [a.to_dict() for a in self.artifacts],
            "events": self.events,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Pipeline":
        return cls(
            pipeline_id=PipelineId.from_dict(data["pipeline_id"]),
            name=str(data["name"]),
            state=PipelineState(data["state"]),
            tasks=list(data.get("tasks", [])),
            artifacts=[Artifact.from_dict(a) for a in data.get("artifacts", [])],
            events=list(data.get("events", [])),
        )
