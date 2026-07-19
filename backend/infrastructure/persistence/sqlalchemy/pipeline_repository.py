from typing import Optional, List
from sqlalchemy.orm import Session
from backend.repositories.pipeline_repository import PipelineRepository
from backend.domain.aggregates.pipeline import Pipeline
from backend.domain.value_objects.pipeline_id import PipelineId
from backend.domain.states import PipelineState
from backend.models import Pipeline as LegacyPipeline, PipelineStatus

class SqlAlchemyPipelineRepository(PipelineRepository):
    """SQLAlchemy implementation of PipelineRepository wrapping Pipeline state management queries."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, entity: Pipeline) -> None:
        pipeline_type = getattr(entity, "metadata", {}).get("pipeline_type", "document_processing_demo")
        from backend.adapters.pipeline_adapter import PipelineAdapter
        legacy_data = PipelineAdapter.domain_to_legacy(entity)
        record = LegacyPipeline(
            id=entity.pipeline_id.value,
            name=entity.name,
            pipeline_type=pipeline_type,
            status=PipelineStatus(legacy_data["status"])
        )
        self.session.add(record)

    def save(self, entity: Pipeline) -> None:
        record = self.session.query(LegacyPipeline).filter(LegacyPipeline.id == entity.pipeline_id.value).first()
        if not record:
            self.create(entity)
        else:
            record.name = entity.name
            from backend.adapters.pipeline_adapter import PipelineAdapter
            legacy_data = PipelineAdapter.domain_to_legacy(entity)
            record.status = PipelineStatus(legacy_data["status"])
            metadata = getattr(entity, "metadata", {})
            if "pipeline_type" in metadata:
                record.pipeline_type = metadata["pipeline_type"]




    def get(self, id: PipelineId) -> Optional[Pipeline]:
        record = self.session.query(LegacyPipeline).filter(LegacyPipeline.id == id.value).first()
        if not record:
            return None
        from backend.adapters.pipeline_adapter import PipelineAdapter
        return PipelineAdapter.legacy_to_domain(record)

    def get_by_id(self, id: PipelineId) -> Optional[Pipeline]:
        return self.get(id)

    def update_state(self, pipeline_id: PipelineId, state: PipelineState) -> None:
        record = self.session.query(LegacyPipeline).filter(LegacyPipeline.id == pipeline_id.value).first()
        if record:
            record.status = PipelineStatus(state.value.lower())

    def resume(self, pipeline_id: PipelineId) -> None:
        self.update_state(pipeline_id, PipelineState.RUNNING)

    def fail(self, pipeline_id: PipelineId, error_message: str) -> None:
        record = self.session.query(LegacyPipeline).filter(LegacyPipeline.id == pipeline_id.value).first()
        if record:
            record.status = PipelineStatus.failed
            # If the database model has error message field, set it
            if hasattr(record, "error_message"):
                record.error_message = error_message

    def get_by_state(self, state: PipelineState) -> Optional[Pipeline]:
        record = self.session.query(LegacyPipeline).filter(LegacyPipeline.status == PipelineStatus(state.value.lower())).first()
        if not record:
            return None
        from backend.adapters.pipeline_adapter import PipelineAdapter
        return PipelineAdapter.legacy_to_domain(record)

    def delete(self, id: PipelineId) -> None:
        record = self.session.query(LegacyPipeline).filter(LegacyPipeline.id == id.value).first()
        if record:
            self.session.delete(record)

    def list(self) -> List[Pipeline]:
        records = self.session.query(LegacyPipeline).all()
        from backend.adapters.pipeline_adapter import PipelineAdapter
        return [PipelineAdapter.legacy_to_domain(r) for r in records]

    def health(self) -> dict:
        try:
            self.session.execute("SELECT 1")
            return {"status": "healthy", "type": "pipeline_repository"}
        except Exception as e:
            return {"status": "unhealthy", "type": "pipeline_repository", "error": str(e)}
