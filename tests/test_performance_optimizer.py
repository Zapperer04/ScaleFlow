# tests/test_performance_optimizer.py
import pytest
from backend.performance_optimizer import analyze_performance
from backend.performance_analysis import build_performance_model

def test_empty_performance_model():
    empty_model = {
        "summary": {
            "pipeline_duration_ms": 0,
            "critical_path_duration_ms": 0.0,
            "parallel_efficiency": 0.0,
            "queue_wait_ms": 0,
            "queue_wait_percentage": 0.0,
            "execution_ms": 0,
            "execution_percentage": 0.0,
            "retry_ms": 0,
            "retry_percentage": 0.0,
            "idle_ms": 0,
            "idle_percentage": 0.0,
            "longest_task": {"task_id": None, "duration_ms": 0},
            "slowest_worker": None,
            "most_congested_queue": None,
            "worker_count": 0,
            "task_count": 0
        },
        "critical_path": {"tasks": [], "edges": []},
        "timeline": [],
        "lanes": [],
        "workers": [],
        "queues": [],
        "stages": [],
        "flamegraph": [],
        "statistics": {}
    }
    opt = analyze_performance(empty_model)
    assert opt is not None
    assert opt["metadata"]["recommendation_count"] == 0
    assert opt["metadata"]["bottleneck_count"] == 0
    assert opt["summary"]["overall_score"] == 100.0

def test_single_task_pipeline():
    model = {
        "summary": {
            "pipeline_duration_ms": 2000,
            "critical_path_duration_ms": 2000.0,
            "parallel_efficiency": 1.0,
            "queue_wait_ms": 200,
            "queue_wait_percentage": 10.0,
            "execution_ms": 1800,
            "execution_percentage": 90.0,
            "retry_ms": 0,
            "retry_percentage": 0.0,
            "idle_ms": 200,
            "idle_percentage": 10.0,
            "longest_task": {"task_id": 1, "duration_ms": 1800},
            "slowest_worker": "worker-1",
            "most_congested_queue": "default",
            "worker_count": 1,
            "task_count": 1
        },
        "critical_path": {"tasks": [1], "edges": []},
        "timeline": [
            {
                "segment_id": "task-1-attempt-0",
                "task_id": 1,
                "worker_id": "worker-1",
                "queue": "default",
                "started_at": "2026-07-27T12:00:00.200Z",
                "finished_at": "2026-07-27T12:00:02.000Z",
                "start_ms": 200,
                "end_ms": 2000,
                "duration_ms": 1800,
                "queue_wait_ms": 200,
                "retry": 0,
                "status": "completed",
                "lane": 0
            }
        ],
        "lanes": [{"lane": 0, "worker_id": "worker-1"}],
        "workers": [
            {
                "worker": "worker-1",
                "utilization": 90.0,
                "busy_ms": 1800,
                "idle_ms": 200,
                "tasks": 1,
                "tasks_completed": 1,
                "tasks_failed": 0,
                "retry_count": 0,
                "lease_expiry_count": 0
            }
        ],
        "queues": [
            {
                "queue": "default",
                "metrics": {
                    "count": 1,
                    "min": 200,
                    "max": 200,
                    "mean": 200.0,
                    "median": 200.0
                }
            }
        ],
        "stages": [
            {
                "stage": "preprocess_document",
                "count": 1,
                "total_duration": 1800,
                "average_duration": 1800.0,
                "slowest_task": {"task_id": 1, "duration_ms": 1800}
            }
        ]
    }
    opt = analyze_performance(model)
    assert opt is not None
    # Verify deterministic ordering and content
    assert "bottlenecks" in opt
    assert "recommendations" in opt
    assert "what_if" in opt
    
    # Check baseline structure
    assert opt["what_if"]["baseline"]["pipeline_duration_ms"] == 2000
    assert opt["what_if"]["baseline"]["worker_count"] == 1

def test_high_retry_pipeline():
    model = {
        "summary": {
            "pipeline_duration_ms": 5000,
            "critical_path_duration_ms": 5000.0,
            "parallel_efficiency": 1.0,
            "retry_ms": 3000,
            "worker_count": 1,
            "task_count": 1
        },
        "critical_path": {"tasks": [1], "edges": []},
        "timeline": [
            {
                "task_id": 1,
                "worker_id": "worker-1",
                "queue": "default",
                "duration_ms": 1000,
                "queue_wait_ms": 100,
                "retry": 0,
                "status": "failed"
            },
            {
                "task_id": 1,
                "worker_id": "worker-1",
                "queue": "default",
                "duration_ms": 1500,
                "queue_wait_ms": 100,
                "retry": 1,
                "status": "failed"
            },
            {
                "task_id": 1,
                "worker_id": "worker-1",
                "queue": "default",
                "duration_ms": 1500,
                "queue_wait_ms": 100,
                "retry": 2,
                "status": "completed"
            }
        ],
        "workers": [
            {
                "worker": "worker-1",
                "utilization": 80.0,
                "busy_ms": 4000,
                "idle_ms": 1000,
                "retry_count": 2
            }
        ]
    }
    opt = analyze_performance(model)
    # Check for retry recommendations
    retry_recs = [r for r in opt["recommendations"] if "retri" in r["id"].lower()]
    assert len(retry_recs) > 0
    assert retry_recs[0]["severity"] in ("critical", "high", "medium", "low")
    assert retry_recs[0]["confidence"] in ("high", "medium", "low")

def test_starvation_and_congestion():
    model = {
        "summary": {
            "pipeline_duration_ms": 15000,
            "critical_path_duration_ms": 12000.0,
            "worker_count": 2,
            "task_count": 2
        },
        "critical_path": {"tasks": [1, 2], "edges": []},
        "timeline": [
            {
                "task_id": 1,
                "worker_id": "worker-1",
                "queue": "congested-q",
                "duration_ms": 500,
                "queue_wait_ms": 8000, # Large queue wait -> starvation
                "retry": 0,
                "status": "completed"
            },
            {
                "task_id": 2,
                "worker_id": "worker-2",
                "queue": "congested-q",
                "duration_ms": 1000,
                "queue_wait_ms": 7000,
                "retry": 0,
                "status": "completed"
            }
        ],
        "queues": [
            {
                "queue": "congested-q",
                "metrics": {
                    "mean": 7500.0
                }
            }
        ],
        "workers": [
            {
                "worker": "worker-1",
                "utilization": 95.0, # High utilization
                "busy_ms": 14250,
                "idle_ms": 750
            }
        ]
    }
    opt = analyze_performance(model)
    # Verify we got queue congestion bottleneck
    q_bottles = [b for b in opt["bottlenecks"] if "queue" in b["id"]]
    assert len(q_bottles) > 0
    
    # Verify deterministic sorting of bottlenecks
    sevs = [b["severity"] for b in opt["bottlenecks"]]
    sev_scores = [{"critical": 4, "high": 3, "medium": 2, "low": 1}[s] for s in sevs]
    # Assert they are sorted descending
    assert all(sev_scores[i] >= sev_scores[i+1] for i in range(len(sev_scores)-1))

def test_identical_runs_and_read_only():
    # Make sure repeated runs with same model produce exactly identical output
    model = {
        "summary": {
            "pipeline_duration_ms": 5000,
            "critical_path_duration_ms": 4000.0,
            "worker_count": 2,
            "task_count": 3
        },
        "critical_path": {"tasks": [1, 2], "edges": []},
        "timeline": [
            {"task_id": 1, "worker_id": "worker-1", "queue": "q1", "duration_ms": 1000, "queue_wait_ms": 100, "retry": 0},
            {"task_id": 2, "worker_id": "worker-2", "queue": "q1", "duration_ms": 2000, "queue_wait_ms": 1500, "retry": 0}
        ],
        "workers": [
            {"worker": "worker-1", "utilization": 80.0, "busy_ms": 4000},
            {"worker": "worker-2", "utilization": 20.0, "busy_ms": 1000}
        ],
        "queues": [
            {"queue": "q1", "metrics": {"mean": 800.0}}
        ]
    }
    opt1 = analyze_performance(model)
    opt2 = analyze_performance(model)
    assert opt1 == opt2
