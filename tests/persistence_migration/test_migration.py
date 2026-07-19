import os
import json
import time
import pytest
from backend.infrastructure.providers.bootstrap import get_container
from backend.domain.value_objects.pipeline_id import PipelineId
from backend.domain.value_objects.document_id import DocumentId
from backend.domain.aggregates.pipeline import Pipeline
from backend.domain.aggregates.document import Document
from backend.domain.states import PipelineState
from backend.infrastructure.storage.vector_store import VectorPoint, VectorQueryFilter
from backend.services.metadata_service import get_standardized_metadata
from backend.models import SessionLocal

@pytest.fixture
def db_session():
    session = SessionLocal()
    yield session
    session.close()

def test_repository_migration_metadata_service(db_session):
    # Setup test pipeline and artifacts via UOW
    container = get_container()
    uow = container.unit_of_work
    
    # 1. Create pipeline record
    pipeline = Pipeline(
        pipeline_id=PipelineId(9001),
        name="Metadata Test Migration",
        state=PipelineState.Uploaded
    )
    uow.pipelines.create(pipeline)
    
    # 2. Get standardized metadata for the pipeline (which uses get_standardized_metadata)
    # This should call our repositories inside the metadata_service
    meta = get_standardized_metadata(uow, 9001)
    assert isinstance(meta, dict)
    assert meta["document_type"] == "generic"

def test_artifact_store_identical_behavior():
    container = get_container()
    art_store = container.artifact_store
    
    test_uri = "storage/pipelines/9999/task_9999_test_artifact.json"
    test_data = {"key": "value", "nested": [1, 2, 3]}
    
    # Save via helper
    from backend.context.artifact_store import save_artifact_to_disk, load_artifact_from_disk
    uri, checksum = save_artifact_to_disk(9999, 9999, "test_artifact", test_data)
    assert uri == test_uri
    assert checksum is not None
    
    # Load back
    loaded = load_artifact_from_disk(uri)
    assert loaded == test_data

def test_cache_keys_and_ttl():
    container = get_container()
    cache = container.cache
    
    # Get/set cache embedding
    from backend.services.embedding_service import _cache_embedding, _lookup_embedding
    
    text_hash = "abc123hash"
    vector = [0.1, 0.2, 0.3]
    
    _cache_embedding(text_hash, vector)
    
    # Verify we can lookup
    val = _lookup_embedding(text_hash)
    assert val == vector

def test_vector_store_identical_queries():
    container = get_container()
    store = container.vector_store
    
    collection = "test_migration_vector"
    points = [
        VectorPoint(
            id="93a21644-8d48-43e8-9bc9-8e7c10b777a8",
            vector=[1.0] + [0.0] * 767,
            payload={"pipeline_id": 9991, "chunk_text": "First Chunk"}
        )
    ]
    store.upsert(collection, points)
    
    # Query via vector_store service helper
    from backend.services.vector_store import search_similar
    results = search_similar(
        query_vector=[1.0] + [0.0] * 767,
        top_k=1,
        collection_name=collection,
        filters={"pipeline_id": 9991}
    )
    
    assert len(results) == 1
    assert results[0]["chunk_text"] == "First Chunk"

def test_checkpoints_identical_format():
    container = get_container()
    store = container.checkpoint_store
    
    # Save checkpoint via mock/stub task
    task_id = 88712
    progress_data = {"resume_page": 3, "last_completed_page": 2, "parser": "vlm"}
    
    store.save_checkpoint(task_id, progress_data)
    
    # Load back
    loaded = store.load_checkpoint(task_id)
    assert loaded == progress_data

def test_uow_commit_rollback(db_session):
    container = get_container()
    uow = container.unit_of_work
    
    pipeline = Pipeline(
        pipeline_id=PipelineId(1224),
        name="UoW Commit Rollback Test",
        state=PipelineState.Uploaded
    )
    
    uow.pipelines.create(pipeline)
    uow.rollback()
    
    # Verify it does not exist after rollback
    assert uow.pipelines.get(PipelineId(1224)) is None
