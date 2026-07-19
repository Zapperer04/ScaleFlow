import pytest
from execution_engine.core.job import JobSpec
from execution_engine.core.artifact import ArtifactRef
from execution_engine.core.requirements import ProviderRequirements
from execution_engine.worker import ExecutionWorker
from execution_engine.control_plane.scheduler import InterleavedFairQueue

def test_worker_death_resilience(mocker):
    mock_lease_manager = mocker.MagicMock()
    
    mock_provider = mocker.MagicMock()
    mock_provider.get_provider_id.return_value = "mock-provider"
    mock_provider.parse.return_value = {"nodes": []}
    
    mock_broker = mocker.MagicMock()
    mock_broker.acquire.return_value = mock_provider
    
    mock_quota = mocker.MagicMock()
    mock_quota.acquire_quota.return_value = True
    
    mock_registry = mocker.MagicMock()
    mock_registry.store.return_value = mocker.MagicMock(uri="file://test")
    
    job = JobSpec(
        id="job-1",
        type="test",
        payload=ArtifactRef(artifact_id="art-1", uri="test", version="1", content_type="test"),
        requirements=ProviderRequirements()
    )
    
    # Mocking first worker's lease acquisition, then a second worker picks it up
    mock_lease_manager.acquire_lease.return_value = "lease-456"
    
    worker2 = ExecutionWorker(
        broker=mock_broker,
        quota_manager=mock_quota,
        lease_manager=mock_lease_manager,
        artifact_registry=mock_registry,
        validation_pipeline=mocker.MagicMock(),
        status_service=mocker.MagicMock(),
        health_service=mocker.MagicMock()
    )
    worker2.validator.validate.return_value = {"nodes": []}
    
    assert worker2.execute_job(job, "trace-1") == True

def test_global_429_storm(mocker):
    mock_quota_manager = mocker.MagicMock()
    mock_quota_manager.acquire_quota.return_value = False
    
    mock_provider = mocker.MagicMock()
    mock_provider.get_provider_id.return_value = "mock-provider"
    mock_broker = mocker.MagicMock()
    mock_broker.acquire.return_value = mock_provider
    
    job = JobSpec(
        id="job-2",
        type="test",
        payload=ArtifactRef(artifact_id="art-2", uri="test", version="1", content_type="test"),
        requirements=ProviderRequirements()
    )
    
    worker = ExecutionWorker(
        broker=mock_broker,
        quota_manager=mock_quota_manager,
        lease_manager=mocker.MagicMock(),
        artifact_registry=mocker.MagicMock(),
        validation_pipeline=mocker.MagicMock(),
        status_service=mocker.MagicMock(),
        health_service=mocker.MagicMock()
    )
    
    result = worker.execute_job(job, "trace-2")
    assert result == False

def test_mixed_document_chaos_integration(mocker):
    queue = InterleavedFairQueue()
    docs = {
        "Doc_A": 150,
        "Doc_B": 2,
        "Doc_C": 5,
        "Doc_D": 30,
        "Doc_E": 1,
        "Doc_F": 80
    }
    for doc_id, pages in docs.items():
        for page_idx in range(pages):
            job = JobSpec(
                id=f"{doc_id}-page-{page_idx}",
                type="parse_page",
                payload=ArtifactRef(artifact_id=f"art-{doc_id}-{page_idx}", uri="test", version="1", content_type="test"),
                requirements=ProviderRequirements(multimodal=True),
                metadata={"document_id": doc_id}
            )
            queue.push(job)
    first_pops = [queue.pop().metadata["document_id"] for _ in range(6)]
    assert len(set(first_pops)) > 1
