# backend/adaptive_scheduler.py
import time
from datetime import datetime

def build_scheduling_advisor(replay_model, performance_model, optimization_model, forecast_model):
    """
    Builds a deterministic Scheduling Advisor model using ONLY replay, performance,
    optimization, and forecast models. This is a read-only analysis layer.
    """
    version = 1
    generated_at = datetime.utcnow().isoformat() + "Z"

    # Extract base variables
    summary_model = performance_model.get("summary", {})
    timeline = performance_model.get("timeline", [])
    workers_list = performance_model.get("workers", [])
    queues_list = performance_model.get("queues", [])
    critical_path_tasks = set(performance_model.get("critical_path", {}).get("tasks", []))
    pipeline_duration_ms = summary_model.get("pipeline_duration_ms", 0)

    # 1. Worker Analysis
    overloaded_workers = 0
    idle_workers = 0
    worker_saturation = 0
    worker_starvation = 0
    worker_details = []
    utilizations = []

    for w in workers_list:
        w_name = w.get("worker")
        util = float(w.get("utilization", 0.0))
        utilizations.append(util)

        # Count critical path tasks on this worker
        critical_tasks_count = sum(
            1 for seg in timeline
            if seg.get("worker_id") == w_name and seg.get("task_id") in critical_path_tasks
        )

        # Sum queue wait for tasks run on this worker
        q_wait_sum = sum(
            float(seg.get("queue_wait_ms") or 0.0)
            for seg in timeline
            if seg.get("worker_id") == w_name
        )

        # Status rules
        if util > 80.0:
            status = "overloaded"
            overloaded_workers += 1
        elif util < 15.0:
            status = "idle"
            idle_workers += 1
        else:
            status = "balanced"

        if util > 90.0:
            worker_saturation += 1
        
        # Starvation: idle worker when tasks were queued overall
        if util < 15.0 and len(timeline) > 0:
            worker_starvation += 1

        worker_details.append({
            "worker": w_name,
            "busy_ms": int(w.get("busy_ms", 0)),
            "idle_ms": int(w.get("idle_ms", 0)),
            "utilization": round(util, 2),
            "queue_wait": round(q_wait_sum, 2),
            "critical_tasks": critical_tasks_count,
            "status": status
        })

    # Sort Worker Analysis deterministically: Utilization DESC, Busy Time DESC, Worker ID ASC
    worker_details.sort(key=lambda x: (-x["utilization"], -x["busy_ms"], x["worker"]))

    # Utilization variance
    if utilizations:
        mean_util = sum(utilizations) / len(utilizations)
        util_variance = sum((u - mean_util) ** 2 for u in utilizations) / len(utilizations)
    else:
        util_variance = 0.0

    worker_analysis = {
        "overloaded_workers": overloaded_workers,
        "idle_workers": idle_workers,
        "worker_imbalance": overloaded_workers + idle_workers,
        "worker_saturation": worker_saturation,
        "worker_starvation": worker_starvation,
        "utilization_variance": round(util_variance, 2),
        "workers": worker_details
    }

    # 2. Queue Analysis
    queue_details = []
    congested_queues_count = 0
    starved_queues_count = 0
    monopolized_queues_count = 0
    total_tasks = sum(q.get("metrics", {}).get("count", 0) for q in queues_list) or 1

    for q in queues_list:
        q_name = q.get("queue")
        metrics = q.get("metrics", {})
        avg_wait = float(metrics.get("mean", 0.0))
        max_wait = float(metrics.get("max", 0.0))
        q_count = metrics.get("count", 0)

        # Severity criteria
        if avg_wait > 3000.0 or max_wait > 8000.0:
            severity = "high"
            congested_queues_count += 1
        elif avg_wait > 1000.0 or max_wait > 3000.0:
            severity = "medium"
            congested_queues_count += 1
        elif avg_wait > 0.0:
            severity = "low"
        else:
            severity = "none"

        # Starvation: long queue wait but some workers are idle
        if avg_wait > 1500.0 and idle_workers > 0:
            starved_queues_count += 1

        # Monopolization: queue contains > 80% of all tasks
        if q_count / total_tasks > 0.8:
            monopolized_queues_count += 1

        queue_details.append({
            "queue": q_name,
            "severity": severity,
            "average_wait_ms": round(avg_wait, 2),
            "max_wait_ms": round(max_wait, 2)
        })

    # Sort queues by average_wait_ms DESC, then queue name ASC
    queue_details.sort(key=lambda x: (-x["average_wait_ms"], x["queue"]))

    # Uneven load: diff between max and min queue avg wait
    avg_waits = [q["average_wait_ms"] for q in queue_details]
    uneven_queue_load = max(avg_waits) - min(avg_waits) if avg_waits else 0.0

    queue_analysis = {
        "congested_queues": congested_queues_count,
        "starved_queues": starved_queues_count,
        "monopolized_queues": monopolized_queues_count,
        "uneven_queue_load": round(uneven_queue_load, 2),
        "queues": queue_details
    }

    # 3. Critical Path Scheduling
    critical_path_scheduling = []
    for tid in sorted(list(critical_path_tasks)):
        t_segs = [s for s in timeline if s.get("task_id") == tid]
        if not t_segs:
            continue
        
        # Check queue wait bottlenecks on critical path
        q_wait = sum(float(s.get("queue_wait_ms") or 0.0) for s in t_segs)
        duration = sum(float(s.get("duration_ms") or 0.0) for s in t_segs)

        if q_wait > 500.0:
            critical_path_scheduling.append({
                "task_id": tid,
                "reason": "critical_path_queue_wait",
                "estimated_gain_ms": int(q_wait)
            })
        elif duration > 2000.0:
            critical_path_scheduling.append({
                "task_id": tid,
                "reason": "removable_bottleneck",
                "estimated_gain_ms": int(duration * 0.3)  # Potential 30% reduction via profiling
            })
        else:
            critical_path_scheduling.append({
                "task_id": tid,
                "reason": "serial_chain",
                "estimated_gain_ms": int(duration * 0.15)
            })

    # Deterministic sort: estimated_gain_ms DESC, task_id ASC
    critical_path_scheduling.sort(key=lambda x: (-x["estimated_gain_ms"], x["task_id"]))

    # 4. Retry Policy Analysis
    total_retries = 0
    task_retries = {}
    expensive_retries_ms = 0.0

    for seg in timeline:
        t_id = seg.get("task_id")
        retry_idx = seg.get("retry") or 0
        if retry_idx > 0:
            total_retries += 1
            task_retries[t_id] = max(task_retries.get(t_id, 0), retry_idx)
            expensive_retries_ms += seg.get("duration_ms") or 0.0

    retry_hotspots = [tid for tid, r_count in task_retries.items() if r_count >= 2]
    retry_storm = total_retries >= 5

    retry_recommendations = []
    if retry_hotspots:
        retry_recommendations.append("exponential_backoff")
        retry_recommendations.append("retry_isolation")
    if retry_storm:
        retry_recommendations.append("retry_reduction")

    retry_analysis = {
        "retry_storm": retry_storm,
        "retry_hotspots": sorted(retry_hotspots),
        "expensive_retries_ms": round(expensive_retries_ms, 2),
        "recommendations": retry_recommendations
    }

    # 5. Autoscaling Advisor
    autoscaling_recommendations = []
    for qd in queue_details:
        q_name = qd["queue"]
        avg_w = qd["average_wait_ms"]
        
        if avg_w > 1000.0:
            # Determine worker type recommended
            if any(term in q_name.lower() for term in ["gpu", "embedding", "ocr", "inference"]):
                worker_type = "gpu"
            elif any(term in q_name.lower() for term in ["cpu", "default", "parsing", "metadata"]):
                worker_type = "cpu"
            else:
                worker_type = "queue"
                
            confidence = "high" if avg_w > 3000.0 else "medium"
            
            # Simple heuristic for estimated gain
            q_tasks_count = next((q.get("metrics", {}).get("count", 0) for q in queues_list if q.get("queue") == q_name), 1)
            est_gain = int(avg_w * q_tasks_count * 0.75)

            autoscaling_recommendations.append({
                "recommendation": "add_worker",
                "queue": q_name,
                "worker_type": worker_type,
                "confidence": confidence,
                "estimated_gain_ms": est_gain
            })

    # Sort autoscaling recommendations: estimated_gain_ms DESC, queue ASC
    autoscaling_recommendations.sort(key=lambda x: (-x["estimated_gain_ms"], x["queue"]))

    # 6. Scheduling Recommendations
    recommendations = []
    rec_counter = 1

    # 6.1 Worker Imbalance / Overloaded worker recommendations
    for w in worker_details:
        if w["status"] == "overloaded":
            recommendations.append({
                "id": f"rec-{rec_counter}",
                "severity": "critical" if w["utilization"] > 90.0 else "high",
                "confidence": "high",
                "category": "worker",
                "title": f"Redistribute Load from {w['worker']}",
                "description": f"Worker {w['worker']} is overloaded ({w['utilization']}% utilization). Move non-critical tasks to idle workers.",
                "estimated_gain_ms": int(w["busy_ms"] * 0.25),
                "affected_tasks": list(set(s.get("task_id") for s in timeline if s.get("worker_id") == w["worker"])),
                "affected_workers": [w["worker"]]
            })
            rec_counter += 1

    # 6.2 Queue Congestion recommendations
    for q in queue_details:
        if q["severity"] in ["high", "medium"]:
            recommendations.append({
                "id": f"rec-{rec_counter}",
                "severity": "critical" if q["severity"] == "high" else "high",
                "confidence": "high" if q["average_wait_ms"] > 2500.0 else "medium",
                "category": "queue",
                "title": f"Increase {q['queue'].capitalize()} Workers",
                "description": f"Queue '{q['queue']}' has significant congestion with average wait time of {q['average_wait_ms'] / 1000.0:.2f}s.",
                "estimated_gain_ms": int(q["average_wait_ms"] * 2.0),
                "affected_tasks": list(set(s.get("task_id") for s in timeline if s.get("queue") == q["queue"])),
                "affected_workers": []
            })
            rec_counter += 1

    # 6.3 Retry hotspots recommendations
    for tid in retry_hotspots:
        recommendations.append({
            "id": f"rec-{rec_counter}",
            "severity": "medium",
            "confidence": "high",
            "category": "retry",
            "title": f"Optimize Retry Policy for Task-{tid}",
            "description": f"Task-{tid} has multiple retries. Implement exponential backoff or retry isolation to save execution time.",
            "estimated_gain_ms": int(expensive_retries_ms / len(retry_hotspots)),
            "affected_tasks": [tid],
            "affected_workers": []
        })
        rec_counter += 1

    # Deterministic sorting function for recommendations
    def get_severity_weight(sev):
        return {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(sev, 0)

    recommendations.sort(key=lambda r: (
        -get_severity_weight(r["severity"]),
        -r["estimated_gain_ms"],
        -{"high": 3, "medium": 2, "low": 1}.get(r["confidence"], 0),
        r["id"]
    ))

    # 7. Scheduling Score
    current_efficiency = float(summary_model.get("parallel_efficiency", 1.0) * 100.0)
    current_efficiency = max(10.0, min(100.0, current_efficiency))

    estimated_time_saved = sum(r["estimated_gain_ms"] for r in recommendations[:3])
    estimated_time_saved = min(estimated_time_saved, int(pipeline_duration_ms * 0.75))

    potential_efficiency = current_efficiency + (estimated_time_saved / (pipeline_duration_ms or 1.0) * 100.0)
    potential_efficiency = max(current_efficiency, min(98.0, potential_efficiency))

    worker_savings = sum(r["estimated_gain_ms"] for r in recommendations if r["category"] == "worker")
    queue_savings = sum(r["estimated_gain_ms"] for r in recommendations if r["category"] == "queue")
    retry_savings = sum(r["estimated_gain_ms"] for r in recommendations if r["category"] == "retry")

    # Score calculation out of 100
    base_score = 100.0
    base_score -= overloaded_workers * 15.0
    base_score -= congested_queues_count * 10.0
    base_score -= len(retry_hotspots) * 8.0
    base_score -= (idle_workers > 0 and congested_queues_count > 0) * 10.0  # penalty for starvation
    scheduling_score_val = max(10.0, min(100.0, base_score))

    scheduling_score = {
        "score": round(scheduling_score_val, 1),
        "current_efficiency": round(current_efficiency, 2),
        "potential_efficiency": round(potential_efficiency, 2),
        "estimated_time_saved_ms": estimated_time_saved,
        "savings": {
            "worker_ms": worker_savings,
            "queue_ms": queue_savings,
            "retry_ms": retry_savings
        }
    }

    # 8. Local Simulation Model (coefficients only)
    total_queue_wait = sum(float(seg.get("queue_wait_ms") or 0.0) for seg in timeline)
    avg_worker_util = sum(utilizations) / len(utilizations) if utilizations else 0.0

    simulation = {
        "baseline": {
            "duration_ms": pipeline_duration_ms,
            "critical_path_ms": float(summary_model.get("critical_path_duration_ms") or pipeline_duration_ms),
            "queue_wait_ms": total_queue_wait,
            "utilization": round(avg_worker_util, 2)
        },
        "coefficients": {
            "worker": 0.18,      # Impact of worker scaling on execution duration
            "retry": 0.85,       # Impact of backoff/retry isolation on retry storms
            "queue": 0.22,       # Impact of buffer size/congested queues on queue wait
            "concurrency": 0.35  # Impact of concurrency level limits on overlap
        }
    }

    return {
        "version": version,
        "generated_at": generated_at,
        "advisor": {
            "worker_analysis": worker_analysis,
            "queue_analysis": queue_analysis,
            "critical_path_scheduling": critical_path_scheduling,
            "retry_analysis": retry_analysis,
            "autoscaling": autoscaling_recommendations,
            "recommendations": recommendations,
            "scheduling_score": scheduling_score,
            "simulation": simulation
        }
    }
