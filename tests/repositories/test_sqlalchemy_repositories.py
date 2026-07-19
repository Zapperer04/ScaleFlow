import pytest
from backend.models import SessionLocal, FileRecord, Pipeline as LegacyPipeline
from backend.infrastructure.persistence.sqlalchemy.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork
from backend.domain.value_objects.document_id import DocumentId
from backend.domain.aggregates.document import Document
from backend.domain.value_objects.pipeline_id import PipelineId
from backend.domain.aggregates.pipeline import Pipeline
from backend.domain.states import PipelineState
from backend.domain.entities.artifact import Artifact
from backend.domain.value_objects.artifact_id import ArtifactId

@pytest.fixture
def db_session():
    session = SessionLocal()
    yield session
    session.close()

def test_uow_commit_and_rollback(db_session):
    uow = SqlAlchemyUnitOfWork(db_session)
    
    # 1. Test Rollback
    pipeline = Pipeline(
        pipeline_id=PipelineId(9999),
        name="UOW Test Rollback",
        state=PipelineState.Uploaded
    )
    uow.pipelines.create(pipeline)
    uow.rollback()
    
    # Verify not saved
    assert uow.pipelines.get(PipelineId(9999)) is None

    # 2. Test Commit
    pipeline = Pipeline(
        pipeline_id=PipelineId(9999),
        name="UOW Test Commit",
        state=PipelineState.Uploaded
    )
    uow.pipelines.create(pipeline)
    uow.commit()
    
    # Verify saved
    saved = uow.pipelines.get(PipelineId(9999))
    assert saved is not None
    assert saved.name == "UOW Test Commit"
    
    # Clean up
    uow.pipelines.delete(PipelineId(9999))
    uow.commit()

def test_duplicate_key_error(db_session):
    uow = SqlAlchemyUnitOfWork(db_session)
    
    pipeline = Pipeline(
        pipeline_id=PipelineId(8888),
        name="Pipeline Dup 1",
        state=PipelineState.Uploaded
    )
    uow.pipelines.create(pipeline)
    uow.commit()
    
    # Try adding again with duplicate key
    pipeline_dup = Pipeline(
        pipeline_id=PipelineId(8888),
        name="Pipeline Dup 2",
        state=PipelineState.Uploaded
    )
    
    uow.pipelines.create(pipeline_dup)
    with pytest.raises(Exception):
        uow.commit()
        
    uow.rollback()
    
    # Clean up
    uow.pipelines.delete(PipelineId(8888))
    uow.commit()

def test_missing_record(db_session):
    uow = SqlAlchemyUnitOfWork(db_session)
    # Check non-existent document
    doc = uow.documents.get(DocumentId(999999))
    assert doc is None

def test_nested_rollback_behavior(db_session):
    # SQLAlchemy rollback restores state after savepoints or nested blocks
    uow = SqlAlchemyUnitOfWork(db_session)
    
    # Outer change
    pipeline = Pipeline(
        pipeline_id=PipelineId(7777),
        name="Outer Pipeline",
        state=PipelineState.Uploaded
    )
    uow.pipelines.create(pipeline)
    uow.commit()
    
    # Inner change that gets rolled back
    db_session.begin_nested()
    pipeline_inner = Pipeline(
        pipeline_id=PipelineId(7778),
        name="Inner Pipeline",
        state=PipelineState.Uploaded
    )
    uow.pipelines.create(pipeline_inner)
    db_session.rollback() # Rollback to savepoint
    
    # Verify outer exists, inner does not
    assert uow.pipelines.get(PipelineId(7777)) is not None
    assert uow.pipelines.get(PipelineId(7778)) is None
    
    # Clean up
    uow.pipelines.delete(PipelineId(7777))
    uow.commit()
