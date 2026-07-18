from typing import Dict, Any
from backend.domain.aggregates.pipeline import Pipeline
from backend.dto.pipeline import PipelineStateDTO

class PipelineAdapter:
    @staticmethod
    def legacy_to_domain(legacy_pipeline: Any) -> Pipeline:
        if hasattr(legacy_pipeline, "to_dict"):
            data = legacy_pipeline.to_dict()
        else:
            data = dict(legacy_pipeline)
        
        # In DB model, ID is pipeline id, state is status.
        return Pipeline.from_dict({
            "pipeline_id": data.get("id"),
            "name": data.get("name", "Unknown"),
            "state": data.get("status", "Created").title(),
            "tasks": [],
            "artifacts": [],
            "events": [],
        })

    @staticmethod
    def domain_to_legacy(domain_pipeline: Pipeline) -> Dict[str, Any]:
        return {
            "id": domain_pipeline.pipeline_id.value,
            "name": domain_pipeline.name,
            "status": domain_pipeline.state.value.lower(),
        }

    @staticmethod
    def legacy_to_dto(legacy_pipeline: Any) -> PipelineStateDTO:
        if hasattr(legacy_pipeline, "to_dict"):
            data = legacy_pipeline.to_dict()
        else:
            data = dict(legacy_pipeline)
        return PipelineStateDTO(
            pipeline_id=data.get("id"),
            name=data.get("name", "Unknown"),
            state=data.get("status", "Created").title(),
        )

    @staticmethod
    def dto_to_legacy(dto: PipelineStateDTO) -> Dict[str, Any]:
        return {
            "id": dto.pipeline_id,
            "name": dto.name,
            "status": dto.state.lower(),
        }
