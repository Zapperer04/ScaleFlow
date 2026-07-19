import pytest
from backend.models import SessionLocal, Pipeline as LegacyPipeline, FileRecord, FileStatus, PipelineStatus
from backend.infrastructure.persistence.sqlalchemy.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork
from backend.infrastructure.repositories.legacy_repository_adapter import LegacyRepositoryAdapter
from backend.domain.value_objects.pipeline_id import PipelineId
from backend.adapters.pipeline_adapter import PipelineAdapter

@pytest.fixture
def db_session():
    session = SessionLocal()
    yield session
    session.close()

def test_pipeline_legacy_roundtrip_compatibility(db_session):
    # 1. Create legacy database record
    legacy_rec = LegacyPipeline(
        id=9512,
        name="Compatibility Test Pipeline",
        pipeline_type="document_processing_demo",
        status=PipelineStatus.created
    )
    db_session.add(legacy_rec)
    db_session.commit()
    
    try:
        # 2. Load legacy record and convert to domain using UOW / Adapter
        uow = SqlAlchemyUnitOfWork(db_session)
        domain_pipeline = uow.pipelines.get(PipelineId(9512))
        
        from backend.domain.states import PipelineState
        assert domain_pipeline is not None
        assert domain_pipeline.name == "Compatibility Test Pipeline"
        assert domain_pipeline.state == PipelineState.Uploaded
        
        # 3. Convert domain pipeline back to legacy representation
        legacy_dict = PipelineAdapter.domain_to_legacy(domain_pipeline)
        
        # 4. Compare key attributes for round-trip parity
        assert legacy_dict["id"] == legacy_rec.id
        assert legacy_dict["name"] == legacy_rec.name
        assert legacy_dict["status"] == legacy_rec.status.value.lower()
        
    finally:
        # Clean up
        rec = db_session.query(LegacyPipeline).filter(LegacyPipeline.id == 9512).first()
        if rec:
            db_session.delete(rec)
            db_session.commit()
