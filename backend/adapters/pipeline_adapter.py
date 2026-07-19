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
        
        status_str = (data.get("status") or "created").lower()
        status_map = {
            "created": "Uploaded",
            "running": "Processing",
            "completed": "Ready",
            "failed": "Failed",
            "cancelled": "Cancelled",
            "blocked": "Failed",
            "recovering": "Processing"
        }
        state_val = status_map.get(status_str, "Uploaded")
        
        return Pipeline.from_dict({
            "pipeline_id": data.get("id"),
            "name": data.get("name", "Unknown"),
            "state": state_val,
            "tasks": [],
            "artifacts": [],
            "events": [],
        })


    @staticmethod
    def domain_to_legacy(domain_pipeline: Pipeline) -> Dict[str, Any]:
        state_str = domain_pipeline.state.value
        state_map = {
            "Uploaded": "created",
            "Processing": "running",
            "Preprocessed": "running",
            "Parsed": "running",
            "Chunked": "running",
            "Embedded": "running",
            "Indexed": "running",
            "Ready": "completed",
            "Failed": "failed",
            "Cancelled": "cancelled"
        }
        legacy_status = state_map.get(state_str, "created")
        return {
            "id": domain_pipeline.pipeline_id.value,
            "name": domain_pipeline.name,
            "status": legacy_status,
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
