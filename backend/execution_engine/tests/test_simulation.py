import pytest
import os
import json
import yaml
import time
from unittest.mock import MagicMock, patch
from execution_engine.core.job import JobSpec
from execution_engine.core.artifact import ArtifactRef
from execution_engine.core.requirements import ProviderRequirements
from execution_engine.worker import ExecutionWorker
from execution_engine.control_plane.scheduler import InterleavedFairQueue
from execution_engine.control_plane.broker import DefaultResourceBroker
from execution_engine.control_plane.capabilities import YamlCapabilityRegistry
from execution_engine.control_plane.health import ProviderStatusService, ProviderHealthService

def test_chaos_scenario_logic(mocker):
    """
    Verifies that the worker handles simulated failures (429, timeouts)
    gracefully, updating provider status and health scores.
    """
    mock_redis = mocker.MagicMock()
    # Mock health scoring to return values
    mock_redis.get.return_value = None
    
    status_service = ProviderStatusService(mock_redis)
    health_service = ProviderHealthService(mock_redis)
    
    # 1. Test 429 updates availability
    status_service.mark_unavailable("gemini", ttl_seconds=60)
    mock_redis.set.assert_called_with("provider:gemini:available", "0", ex=60)
    
    # 2. Test health score penalty on failure
    health_service.record_metrics("gemini", latency=1.5, success=False)
    # Get current health (starts at 100.0) -> penalty 25.0 -> event_score 75.0
    # new_health = (0.15 * 75.0) + (0.85 * 100.0) = 96.25
    # decay_boost = 0.01 * (100.0 - 96.25) = 0.0375
    # total new_health = 96.2875
    mock_redis.set.assert_called_with("provider:gemini:health", "96.2875")

def test_fairness_interleaving():
    """
    Verifies that the InterleavedFairQueue processes jobs from different
    documents in an interleaved manner rather than blocking on the largest document first.
    """
    queue = InterleavedFairQueue()
    
    # Push 5 pages for Doc_A, 2 pages for Doc_B
    for page_idx in range(5):
        queue.push(JobSpec(
            id=f"Doc_A-page-{page_idx}",
            type="parse_page",
            payload=ArtifactRef(artifact_id=f"art-A-{page_idx}", uri="test", version="1", content_type="test"),
            requirements=ProviderRequirements(),
            metadata={"document_id": "Doc_A"}
        ))
        
    for page_idx in range(2):
        queue.push(JobSpec(
            id=f"Doc_B-page-{page_idx}",
            type="parse_page",
            payload=ArtifactRef(artifact_id=f"art-B-{page_idx}", uri="test", version="1", content_type="test"),
            requirements=ProviderRequirements(),
            metadata={"document_id": "Doc_B"}
        ))
        
    # Consecutive pops should belong to different documents (interleaved)
    pop1 = queue.pop()
    pop2 = queue.pop()
    
    assert pop1.metadata["document_id"] != pop2.metadata["document_id"]


def test_worker_recovery_under_outage(mocker):
    """
    Tests worker behaviour when the broker fails to acquire any available provider.
    """
    mock_broker = mocker.MagicMock()
    mock_broker.acquire.side_effect = Exception("No capable, available providers found.")
    
    worker = ExecutionWorker(
        broker=mock_broker,
        quota_manager=mocker.MagicMock(),
        lease_manager=mocker.MagicMock(),
        artifact_registry=mocker.MagicMock(),
        validation_pipeline=mocker.MagicMock(),
        status_service=mocker.MagicMock(),
        health_service=mocker.MagicMock()
    )
    
    job = JobSpec(
        id="job-crash-1",
        type="test",
        payload=ArtifactRef(artifact_id="art-crash", uri="test", version="1", content_type="test"),
        requirements=ProviderRequirements()
    )
    
    # Should handle Exception and return False (recoverable error)
    res = worker.execute_job(job, "trace-crash")
    assert res is False
