import pytest
from backend.performance_analysis import build_performance_model

def test_empty_replay():
    empty_replay = {
        "version": 1,
        "pipeline_id": 999,
        "correlation_id": None,
        "started_at": None,
        "finished_at": None,
        "events": [],
        "metadata": {
            "duration": 0
        }
    }
    model = build_performance_model(empty_replay)
    assert model is not None
    assert model["summary"]["pipeline_duration_ms"] == 0
    assert model["summary"]["task_count"] == 0
    assert len(model["critical_path"]["tasks"]) == 0
    assert len(model["timeline"]) == 0
    assert len(model["lanes"]) == 0
    assert len(model["workers"]) == 0
    assert len(model["queues"]) == 0
    assert len(model["stages"]) == 0
    assert len(model["flamegraph"]) == 0

def test_single_task_replay():
    # Single task that enqueues at 1000ms, starts executing at 1200ms, and completes at 2000ms.
    # Total duration = 2000ms.
    single_task_replay = {
        "version": 1,
        "pipeline_id": 100,
        "correlation_id": "corr-single",
        "started_at": "2026-07-27T12:00:00.000Z",
        "finished_at": "2026-07-27T12:00:02.000Z",
        "events": [
            {
                "timestamp": "2026-07-27T12:00:00.000Z",
                "event_type": "task_queued",
                "task_id": 1,
                "task_type": "preprocess_document",
                "worker_id": "worker-1",
                "payload": {"queue": "default"}
            },
            {
                "timestamp": "2026-07-27T12:00:00.200Z",
                "event_type": "task_running",
                "task_id": 1,
                "task_type": "preprocess_document",
                "worker_id": "worker-1",
                "payload": {"queue": "default"}
            },
            {
                "timestamp": "2026-07-27T12:00:02.000Z",
                "event_type": "task_completed",
                "task_id": 1,
                "task_type": "preprocess_document",
                "worker_id": "worker-1",
                "payload": {"queue": "default"}
            }
        ],
        "metadata": {
            "duration": 2.0
        }
    }
    
    model = build_performance_model(single_task_replay)
    assert model is not None
    assert model["summary"]["pipeline_duration_ms"] == 2000
    assert model["summary"]["task_count"] == 1
    
    # Critical path should have the only task
    assert model["critical_path"]["tasks"] == [1]
    
    # Worker utilization: busy_ms = 1800 (from 200ms to 2000ms), idle_ms = 200, utilization = 90%
    assert len(model["workers"]) == 1
    w = model["workers"][0]
    assert w["worker"] == "worker-1"
    assert w["busy_ms"] == 1800
    assert w["idle_ms"] == 200
    assert w["utilization"] == 90.0
    
    # Queue wait
    assert len(model["timeline"]) == 1
    t = model["timeline"][0]
    assert t["queue_wait_ms"] == 200
    assert t["duration_ms"] == 1800
    
    # Lanes
    assert len(model["lanes"]) == 1
    assert model["lanes"][0]["worker_id"] == "worker-1"
    assert model["lanes"][0]["lane"] == 0

def test_multiple_tasks_determinism():
    # Multiple tasks with multiple workers, retries, and dependencies
    replay = {
        "version": 1,
        "pipeline_id": 101,
        "correlation_id": "corr-multi",
        "started_at": "2026-07-27T12:00:00.000Z",
        "finished_at": "2026-07-27T12:00:10.000Z",
        "events": [
            # Task 1: enqueued at 0, starts at 1s, completes at 3s on worker-1
            {"timestamp": "2026-07-27T12:00:00.000Z", "event_type": "task_queued", "task_id": 1, "task_type": "preprocess_document", "worker_id": "worker-1"},
            {"timestamp": "2026-07-27T12:00:01.000Z", "event_type": "task_running", "task_id": 1, "task_type": "preprocess_document", "worker_id": "worker-1"},
            {"timestamp": "2026-07-27T12:00:03.000Z", "event_type": "task_completed", "task_id": 1, "task_type": "preprocess_document", "worker_id": "worker-1"},
            
            # Task 2: enqueued at 3s, starts at 4s, fails at 6s on worker-2
            {"timestamp": "2026-07-27T12:00:03.000Z", "event_type": "task_queued", "task_id": 2, "task_type": "parse_document", "worker_id": "worker-2", "payload": {"dependencies": [1]}},
            {"timestamp": "2026-07-27T12:00:04.000Z", "event_type": "task_running", "task_id": 2, "task_type": "parse_document", "worker_id": "worker-2"},
            {"timestamp": "2026-07-27T12:00:06.000Z", "event_type": "task_failed", "task_id": 2, "task_type": "parse_document", "worker_id": "worker-2"},
            
            # Task 2 Retry (attempt 1): enqueued at 6s, starts at 7s, completes at 9s on worker-1
            {"timestamp": "2026-07-27T12:00:06.000Z", "event_type": "task_retry", "task_id": 2, "task_type": "parse_document", "worker_id": "worker-1"},
            {"timestamp": "2026-07-27T12:00:07.000Z", "event_type": "task_running", "task_id": 2, "task_type": "parse_document", "worker_id": "worker-1"},
            {"timestamp": "2026-07-27T12:00:09.000Z", "event_type": "task_completed", "task_id": 2, "task_type": "parse_document", "worker_id": "worker-1"}
        ],
        "metadata": {
            "duration": 10.0
        }
    }
    
    model1 = build_performance_model(replay)
    model2 = build_performance_model(replay)
    
    # Verify determinism
    assert model1 == model2
    
    # Check stats
    assert model1["summary"]["pipeline_duration_ms"] == 9000
    assert model1["summary"]["worker_count"] == 2
    assert model1["summary"]["task_count"] == 2
    
    # Check timeline attempts
    assert len(model1["timeline"]) == 3
    # Check lanes mapping (worker-1, worker-2 sorted alphabetically)
    assert model1["lanes"][0]["worker_id"] == "worker-1"
    assert model1["lanes"][0]["lane"] == 0
    assert model1["lanes"][1]["worker_id"] == "worker-2"
    assert model1["lanes"][1]["lane"] == 1
    
    # Check flamegraph ordering: start_ms -> depth -> duration -> task_id
    fg = model1["flamegraph"]
    assert len(fg) == 3
    assert fg[0]["task_id"] == 1
    assert fg[1]["task_id"] == 2 # first attempt
    assert fg[2]["task_id"] == 2 # second attempt
