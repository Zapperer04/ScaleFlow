# tests/test_execution_forecaster.py
import pytest
from backend.execution_forecaster import build_execution_forecast

def make_base_perf_model():
    return {
        "summary": {
            "pipeline_duration_ms": 10000,
            "critical_path_duration_ms": 6000.0,
            "parallel_efficiency": 0.6,
            "queue_wait_ms": 1000,
            "queue_wait_percentage": 10.0,
            "execution_ms": 9000,
            "execution_percentage": 90.0,
            "retry_ms": 0,
            "retry_percentage": 0.0,
            "idle_ms": 1000,
            "idle_percentage": 5.0,
            "worker_count": 2,
            "task_count": 4
        },
        "critical_path": {
            "tasks": [1, 2, 4],
            "edges": [[1, 2], [2, 4]]
        },
        "timeline": [
            {
                "segment_id": "task-1-attempt-0",
                "task_id": 1,
                "task_type": "StageA",
                "worker_id": "worker-1",
                "queue": "default",
                "started_at": "2026-07-27T12:00:00.000Z",
                "finished_at": "2026-07-27T12:00:02.000Z",
                "start_ms": 0,
                "end_ms": 2000,
                "duration_ms": 2000,
                "queue_wait_ms": 0,
                "retry": 0,
                "status": "completed",
                "lane": 0
            },
            {
                "segment_id": "task-3-attempt-0",
                "task_id": 3,
                "task_type": "StageB",
                "worker_id": "worker-2",
                "queue": "default",
                "started_at": "2026-07-27T12:00:01.000Z",
                "finished_at": "2026-07-27T12:00:04.000Z",
                "start_ms": 1000,
                "end_ms": 4000,
                "duration_ms": 3000,
                "queue_wait_ms": 1000,
                "retry": 0,
                "status": "completed",
                "lane": 1
            },
            {
                "segment_id": "task-2-attempt-0",
                "task_id": 2,
                "task_type": "StageC",
                "worker_id": "worker-1",
                "queue": "default",
                "started_at": "2026-07-27T12:00:02.000Z",
                "finished_at": None,
                "start_ms": 2000,
                "end_ms": 2000,
                "duration_ms": 0,
                "queue_wait_ms": 0,
                "retry": 0,
                "status": "running",
                "lane": 0
            }
        ],
        "lanes": [
            {"lane": 0, "worker_id": "worker-1"},
            {"lane": 1, "worker_id": "worker-2"}
        ],
        "workers": [
            {
                "worker": "worker-1",
                "utilization": 50.0,
                "busy_ms": 2000,
                "idle_ms": 8000,
                "tasks_completed": 1,
                "tasks_failed": 0,
                "retry_count": 0,
                "lease_expiry_count": 0
            },
            {
                "worker": "worker-2",
                "utilization": 30.0,
                "busy_ms": 3000,
                "idle_ms": 7000,
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
                    "count": 2,
                    "min": 0,
                    "max": 1000,
                    "mean": 500.0,
                    "median": 500.0,
                    "p95": 1000.0,
                    "p99": 1000.0,
                    "std_dev": 500.0
                }
            }
        ],
        "stages": [
            {
                "stage": "StageA",
                "count": 1,
                "total_duration": 2000,
                "average_duration": 2000.0
            },
            {
                "stage": "StageB",
                "count": 1,
                "total_duration": 3000,
                "average_duration": 3000.0
            },
            {
                "stage": "StageC",
                "count": 1,
                "total_duration": 4000,
                "average_duration": 4000.0
            },
            {
                "stage": "StageD",
                "count": 1,
                "total_duration": 1500,
                "average_duration": 1500.0
            }
        ],
        "flamegraph": [
            {
                "task_id": 1,
                "parent_task_id": None,
                "depth": 0,
                "start_ms": 0,
                "duration_ms": 2000,
                "status": "completed",
                "worker_id": "worker-1"
            },
            {
                "task_id": 3,
                "parent_task_id": 1,
                "depth": 1,
                "start_ms": 1000,
                "duration_ms": 3000,
                "status": "completed",
                "worker_id": "worker-2"
            },
            {
                "task_id": 2,
                "parent_task_id": 1,
                "depth": 1,
                "start_ms": 2000,
                "duration_ms": 4000,
                "status": "running",
                "worker_id": "worker-1"
            },
            {
                "task_id": 4,
                "parent_task_id": 2,
                "depth": 2,
                "start_ms": 6000,
                "duration_ms": 1500,
                "status": "pending",
                "worker_id": "worker-2"
            }
        ]
    }

def test_empty_pipeline():
    forecast = build_execution_forecast({}, {})
    assert forecast is not None
    assert forecast["remaining_duration_ms"] == 0.0
    assert forecast["progress"] == 100.0
    assert forecast["confidence"] == "High"

def test_completed_pipeline():
    perf = make_base_perf_model()
    # Change all statuses to completed
    for seg in perf["timeline"]:
        seg["status"] = "completed"
        seg["finished_at"] = "2026-07-27T12:00:06.000Z"
        seg["end_ms"] = 6000
    for fg in perf["flamegraph"]:
        fg["status"] = "completed"
    # Ensure critical path tasks match completed ones
    perf["critical_path"]["tasks"] = [1, 2, 3]
    forecast = build_execution_forecast(perf, {})
    assert forecast["remaining_duration_ms"] == 0.0
    assert forecast["progress"] == 100.0

def test_running_pipeline():
    perf = make_base_perf_model()
    forecast = build_execution_forecast(perf, {})
    assert forecast["remaining_duration_ms"] > 0.0
    assert forecast["progress"] < 100.0
    assert len(forecast["future_tasks"]) > 0

def test_sla_on_track():
    perf = make_base_perf_model()
    # SLA of 20 seconds, forecast should be around 7.5 seconds
    forecast = build_execution_forecast(perf, {}, sla_ms=20000)
    assert forecast["sla_status"] == "On Track"

def test_sla_exceeded():
    perf = make_base_perf_model()
    # SLA of 5 seconds, forecast should exceed it
    forecast = build_execution_forecast(perf, {}, sla_ms=5000)
    assert forecast["sla_status"] in ("Likely Miss", "Missed")

def test_deterministic_sorting():
    perf = make_base_perf_model()
    forecast = build_execution_forecast(perf, {})
    
    # Verify Worker order: likely_finish_ms DESC, worker_id ASC
    workers_out = forecast["worker_forecasts"]
    for i in range(len(workers_out) - 1):
        assert workers_out[i]["likely_finish_ms"] >= workers_out[i+1]["likely_finish_ms"]
        if workers_out[i]["likely_finish_ms"] == workers_out[i+1]["likely_finish_ms"]:
            assert workers_out[i]["worker"] <= workers_out[i+1]["worker"]

    # Verify Stage order: is_critical DESC, remaining_ms DESC, stage ASC
    stages_out = forecast["stage_forecasts"]
    for i in range(len(stages_out) - 1):
        if stages_out[i]["is_critical"] != stages_out[i+1]["is_critical"]:
            assert stages_out[i]["is_critical"] is True and stages_out[i+1]["is_critical"] is False
        else:
            if stages_out[i]["remaining_ms"] != stages_out[i+1]["remaining_ms"]:
                assert stages_out[i]["remaining_ms"] >= stages_out[i+1]["remaining_ms"]
            else:
                assert stages_out[i]["stage"] <= stages_out[i+1]["stage"]

def test_repeated_forecasts():
    perf = make_base_perf_model()
    f1 = build_execution_forecast(perf, {})
    f2 = build_execution_forecast(perf, {})
    assert f1 == f2

def test_confidence_factors():
    perf = make_base_perf_model()
    # Low confidence via lease expiries, queue wait, and zero progress
    perf["workers"][0]["lease_expiry_count"] = 5
    perf["queues"][0]["metrics"]["mean"] = 5000.0
    # Set progress to 0% by marking all timeline tasks pending
    for seg in perf["timeline"]:
        seg["status"] = "pending"
    for fg in perf["flamegraph"]:
        fg["status"] = "pending"
    forecast = build_execution_forecast(perf, {})
    assert forecast["confidence"] in ("Medium", "Low")
