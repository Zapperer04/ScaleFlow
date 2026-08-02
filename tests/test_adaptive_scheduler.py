# tests/test_adaptive_scheduler.py
import pytest
from backend.adaptive_scheduler import build_scheduling_advisor

@pytest.fixture
def empty_models():
    replay_model = {"events": [], "pipeline_id": 1, "correlation_id": "corr-1"}
    performance_model = {
        "summary": {
            "pipeline_duration_ms": 0,
            "critical_path_duration_ms": 0.0,
            "parallel_efficiency": 0.0,
            "queue_wait_ms": 0,
            "execution_ms": 0,
            "retry_ms": 0,
            "idle_ms": 0,
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
    optimization_model = {
        "metadata": {"recommendation_count": 0, "bottleneck_count": 0},
        "summary": {"overall_score": 100.0, "message": "Execution is optimized"},
        "bottlenecks": [],
        "recommendations": []
    }
    forecast_model = {
        "remaining_duration_ms": 0,
        "progress": 100.0,
        "worker_forecasts": [],
        "stage_forecasts": []
    }
    return replay_model, performance_model, optimization_model, forecast_model

def test_empty_pipeline(empty_models):
    rep, perf, opt, fore = empty_models
    res = build_scheduling_advisor(rep, perf, opt, fore)
    
    assert res["version"] == 1
    assert "advisor" in res
    advisor = res["advisor"]
    
    assert advisor["scheduling_score"]["score"] == 100.0
    assert len(advisor["worker_analysis"]["workers"]) == 0
    assert len(advisor["queue_analysis"]["queues"]) == 0
    assert len(advisor["recommendations"]) == 0
    assert len(advisor["autoscaling"]) == 0

def test_completed_pipeline():
    rep = {"events": [{"id": 1}], "pipeline_id": 1, "correlation_id": "c-1"}
    perf = {
        "summary": {
            "pipeline_duration_ms": 5000,
            "critical_path_duration_ms": 2000.0,
            "parallel_efficiency": 0.8,
            "queue_wait_ms": 100,
            "execution_ms": 4800,
            "retry_ms": 0,
            "idle_ms": 200,
            "worker_count": 2,
            "task_count": 4
        },
        "critical_path": {"tasks": [1, 2], "edges": []},
        "timeline": [
            {"task_id": 1, "worker_id": "worker-1", "queue": "default", "duration_ms": 1000, "queue_wait_ms": 10, "retry": 0, "status": "completed"},
            {"task_id": 2, "worker_id": "worker-1", "queue": "default", "duration_ms": 1000, "queue_wait_ms": 20, "retry": 0, "status": "completed"},
            {"task_id": 3, "worker_id": "worker-2", "queue": "embedding", "duration_ms": 1500, "queue_wait_ms": 30, "retry": 0, "status": "completed"},
            {"task_id": 4, "worker_id": "worker-2", "queue": "embedding", "duration_ms": 1300, "queue_wait_ms": 40, "retry": 0, "status": "completed"}
        ],
        "workers": [
            {"worker": "worker-1", "utilization": 40.0, "busy_ms": 2000, "idle_ms": 3000},
            {"worker": "worker-2", "utilization": 56.0, "busy_ms": 2800, "idle_ms": 2200}
        ],
        "queues": [
            {"queue": "default", "metrics": {"count": 2, "mean": 15.0, "max": 20.0}},
            {"queue": "embedding", "metrics": {"count": 2, "mean": 35.0, "max": 40.0}}
        ]
    }
    opt = {
        "metadata": {"recommendation_count": 0, "bottleneck_count": 0},
        "summary": {"overall_score": 100.0, "message": "Optimal execution"},
        "bottlenecks": [],
        "recommendations": []
    }
    fore = {
        "remaining_duration_ms": 0,
        "progress": 100.0,
        "worker_forecasts": [
            {"worker": "worker-1", "predicted_utilization": 40.0, "likely_finish_ms": 2000},
            {"worker": "worker-2", "predicted_utilization": 56.0, "likely_finish_ms": 2800}
        ]
    }
    
    res = build_scheduling_advisor(rep, perf, opt, fore)
    advisor = res["advisor"]
    
    assert advisor["scheduling_score"]["score"] == 100.0
    assert advisor["worker_analysis"]["worker_imbalance"] == 0
    assert len(advisor["recommendations"]) == 0
    assert len(advisor["autoscaling"]) == 0

def test_retry_storm():
    rep = {"events": [{"id": 1}], "pipeline_id": 1, "correlation_id": "c-1"}
    perf = {
        "summary": {
            "pipeline_duration_ms": 8000,
            "critical_path_duration_ms": 4000.0,
            "parallel_efficiency": 0.5,
            "queue_wait_ms": 500,
            "execution_ms": 7500,
            "retry_ms": 4000,
            "idle_ms": 500,
            "worker_count": 1,
            "task_count": 2
        },
        "critical_path": {"tasks": [1], "edges": []},
        "timeline": [
            {"task_id": 1, "worker_id": "worker-1", "queue": "default", "duration_ms": 1000, "queue_wait_ms": 100, "retry": 0, "status": "failed"},
            {"task_id": 1, "worker_id": "worker-1", "queue": "default", "duration_ms": 1000, "queue_wait_ms": 100, "retry": 1, "status": "failed"},
            {"task_id": 1, "worker_id": "worker-1", "queue": "default", "duration_ms": 1000, "queue_wait_ms": 100, "retry": 2, "status": "failed"},
            {"task_id": 1, "worker_id": "worker-1", "queue": "default", "duration_ms": 1000, "queue_wait_ms": 100, "retry": 3, "status": "completed"},
            {"task_id": 2, "worker_id": "worker-1", "queue": "default", "duration_ms": 1500, "queue_wait_ms": 100, "retry": 0, "status": "completed"}
        ],
        "workers": [
            {"worker": "worker-1", "utilization": 68.75, "busy_ms": 5500, "idle_ms": 2500}
        ],
        "queues": [
            {"queue": "default", "metrics": {"count": 5, "mean": 100.0, "max": 100.0}}
        ]
    }
    opt = {
        "metadata": {"recommendation_count": 1, "bottleneck_count": 1},
        "summary": {"overall_score": 75.0, "message": "Excessive retries"},
        "bottlenecks": [{"id": "excessive-retries", "severity": "high"}],
        "recommendations": []
    }
    fore = {
        "remaining_duration_ms": 0,
        "progress": 100.0,
        "worker_forecasts": []
    }
    
    res = build_scheduling_advisor(rep, perf, opt, fore)
    advisor = res["advisor"]
    
    assert advisor["retry_analysis"]["retry_storm"] is False  # total retries = 3 (< 5)
    assert 1 in advisor["retry_analysis"]["retry_hotspots"]  # max retry count is 3 (>= 2)
    assert advisor["retry_analysis"]["expensive_retries_ms"] == 3000.0  # three retries of 1000ms each
    assert "exponential_backoff" in advisor["retry_analysis"]["recommendations"]
    assert "retry_isolation" in advisor["retry_analysis"]["recommendations"]

def test_worker_imbalance_and_sorting():
    rep = {"events": [{"id": 1}], "pipeline_id": 1, "correlation_id": "c-1"}
    perf = {
        "summary": {
            "pipeline_duration_ms": 10000,
            "critical_path_duration_ms": 8000.0,
            "parallel_efficiency": 0.4,
            "queue_wait_ms": 1000,
            "execution_ms": 12000,
            "retry_ms": 0,
            "idle_ms": 8000,
            "worker_count": 3,
            "task_count": 5
        },
        "critical_path": {"tasks": [1, 2, 3], "edges": []},
        "timeline": [
            {"task_id": 1, "worker_id": "worker-1", "queue": "default", "duration_ms": 4000, "queue_wait_ms": 100, "retry": 0, "status": "completed"},
            {"task_id": 2, "worker_id": "worker-1", "queue": "default", "duration_ms": 5000, "queue_wait_ms": 100, "retry": 0, "status": "completed"},
            {"task_id": 3, "worker_id": "worker-2", "queue": "embedding", "duration_ms": 2000, "queue_wait_ms": 100, "retry": 0, "status": "completed"},
            {"task_id": 4, "worker_id": "worker-3", "queue": "embedding", "duration_ms": 500, "queue_wait_ms": 100, "retry": 0, "status": "completed"},
            {"task_id": 5, "worker_id": "worker-3", "queue": "embedding", "duration_ms": 500, "queue_wait_ms": 100, "retry": 0, "status": "completed"}
        ],
        "workers": [
            {"worker": "worker-1", "utilization": 90.0, "busy_ms": 9000, "idle_ms": 1000},
            {"worker": "worker-2", "utilization": 20.0, "busy_ms": 2000, "idle_ms": 8000},
            {"worker": "worker-3", "utilization": 10.0, "busy_ms": 1000, "idle_ms": 9000}
        ],
        "queues": [
            {"queue": "default", "metrics": {"count": 2, "mean": 100.0, "max": 100.0}},
            {"queue": "embedding", "metrics": {"count": 3, "mean": 100.0, "max": 100.0}}
        ]
    }
    opt = {
        "metadata": {"recommendation_count": 1, "bottleneck_count": 1},
        "summary": {"overall_score": 60.0, "message": "Worker imbalance"},
        "bottlenecks": [],
        "recommendations": []
    }
    fore = {
        "remaining_duration_ms": 0,
        "progress": 100.0,
        "worker_forecasts": []
    }
    
    res = build_scheduling_advisor(rep, perf, opt, fore)
    advisor = res["advisor"]
    
    assert advisor["worker_analysis"]["overloaded_workers"] == 1  # worker-1 has 90% utilization
    assert advisor["worker_analysis"]["idle_workers"] == 1       # worker-3 has 10% utilization (< 15%)
    assert advisor["worker_analysis"]["worker_imbalance"] == 2
    
    # Sorting check: Utilization DESC
    workers = advisor["worker_analysis"]["workers"]
    assert workers[0]["worker"] == "worker-1"
    assert workers[1]["worker"] == "worker-2"
    assert workers[2]["worker"] == "worker-3"

def test_queue_starvation_and_autoscaling():
    rep = {"events": [{"id": 1}], "pipeline_id": 1, "correlation_id": "c-1"}
    perf = {
        "summary": {
            "pipeline_duration_ms": 10000,
            "critical_path_duration_ms": 8000.0,
            "parallel_efficiency": 0.4,
            "queue_wait_ms": 5000,
            "execution_ms": 6000,
            "retry_ms": 0,
            "idle_ms": 4000,
            "worker_count": 2,
            "task_count": 2
        },
        "critical_path": {"tasks": [1], "edges": []},
        "timeline": [
            {"task_id": 1, "worker_id": "worker-1", "queue": "embedding", "duration_ms": 3000, "queue_wait_ms": 4000, "retry": 0, "status": "completed"},
            {"task_id": 2, "worker_id": "worker-2", "queue": "default", "duration_ms": 3000, "queue_wait_ms": 1000, "retry": 0, "status": "completed"}
        ],
        "workers": [
            {"worker": "worker-1", "utilization": 30.0, "busy_ms": 3000, "idle_ms": 7000},
            {"worker": "worker-2", "utilization": 30.0, "busy_ms": 3000, "idle_ms": 7000}
        ],
        "queues": [
            {"queue": "embedding", "metrics": {"count": 1, "mean": 4000.0, "max": 4000.0}},
            {"queue": "default", "metrics": {"count": 1, "mean": 1000.0, "max": 1000.0}}
        ]
    }
    opt = {
        "metadata": {"recommendation_count": 1, "bottleneck_count": 1},
        "summary": {"overall_score": 50.0, "message": "Queue wait"},
        "bottlenecks": [],
        "recommendations": []
    }
    fore = {
        "remaining_duration_ms": 0,
        "progress": 100.0,
        "worker_forecasts": []
    }
    
    res = build_scheduling_advisor(rep, perf, opt, fore)
    advisor = res["advisor"]
    
    # embedding: avg wait 4000 > 3000 -> severity "high"
    # default: avg wait 1000 -> severity "low" or "none" (not medium as wait > 1000 is required, mean = 1000.0 is <= 1000.0 in our code check)
    assert advisor["queue_analysis"]["congested_queues"] == 1
    
    embedding_queue = next(q for q in advisor["queue_analysis"]["queues"] if q["queue"] == "embedding")
    assert embedding_queue["severity"] == "high"
    
    # Autoscaling: embedding queue wait > 1000, queue contains "embedding" -> worker_type "gpu"
    gpu_autoscaling = next(a for a in advisor["autoscaling"] if a["queue"] == "embedding")
    assert gpu_autoscaling["worker_type"] == "gpu"
    assert gpu_autoscaling["recommendation"] == "add_worker"
    assert gpu_autoscaling["confidence"] == "high"

def test_simulation_coefficients(empty_models):
    rep, perf, opt, fore = empty_models
    perf["summary"]["pipeline_duration_ms"] = 5000
    perf["summary"]["critical_path_duration_ms"] = 3000.0
    res = build_scheduling_advisor(rep, perf, opt, fore)
    advisor = res["advisor"]
    
    assert "simulation" in advisor
    assert advisor["simulation"]["baseline"]["duration_ms"] == 5000
    assert advisor["simulation"]["baseline"]["critical_path_ms"] == 3000.0
    assert "coefficients" in advisor["simulation"]
    assert "worker" in advisor["simulation"]["coefficients"]
    assert "retry" in advisor["simulation"]["coefficients"]
    assert "queue" in advisor["simulation"]["coefficients"]
    assert "concurrency" in advisor["simulation"]["coefficients"]
