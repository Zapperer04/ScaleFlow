# backend/performance_optimizer.py
import math
from datetime import datetime

def analyze_performance(performance_model):
    """
    Analyzes the Performance Model to extract bottlenecks, recommendations,
    what-if simulation coefficients, and heatmaps.
    
    Args:
        performance_model (dict): Performance Model dictionary conforming to version 1 contract.
        
    Returns:
        dict: Optimization Model dict conforming to version 1 contract.
    """
    if not performance_model or not isinstance(performance_model, dict):
        performance_model = {}

    summary_pm = performance_model.get("summary") or {}
    timeline = performance_model.get("timeline") or []
    workers = performance_model.get("workers") or []
    queues = performance_model.get("queues") or []
    stages = performance_model.get("stages") or []
    critical_path = performance_model.get("critical_path") or {}
    critical_path_tasks = set(critical_path.get("tasks") or [])

    pipeline_duration_ms = summary_pm.get("pipeline_duration_ms") or 0
    worker_count = summary_pm.get("worker_count") or len(workers) or 1

    # Extract critical path components
    critical_path_execution_ms = 0.0
    critical_path_queue_wait_ms = 0.0
    critical_path_retry_ms = 0.0
    
    # Track retries in general
    total_retries = 0
    total_retry_duration_ms = 0.0
    
    for seg in timeline:
        task_id = seg.get("task_id")
        duration = seg.get("duration_ms") or 0.0
        q_wait = seg.get("queue_wait_ms") or 0.0
        retry_idx = seg.get("retry") or 0
        
        if retry_idx > 0:
            total_retries += 1
            total_retry_duration_ms += duration
            
        if task_id in critical_path_tasks:
            critical_path_execution_ms += duration
            critical_path_queue_wait_ms += q_wait
            if retry_idx > 0:
                critical_path_retry_ms += duration

    # 1. IDENTIFY BOTTLENECK CARDS
    bottlenecks = []
    
    # Bottleneck severity helper
    def get_severity_score(severity):
        return {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(severity, 1)

    # 1.1 Longest queue waits
    longest_queue_wait = 0.0
    congested_q_name = None
    for q in queues:
        metrics = q.get("metrics") or {}
        mean_wait = metrics.get("mean") or 0.0
        if mean_wait > longest_queue_wait:
            longest_queue_wait = mean_wait
            congested_q_name = q.get("queue")
            
    if congested_q_name and longest_queue_wait > 500:
        severity = "medium"
        if longest_queue_wait > 5000:
            severity = "critical"
        elif longest_queue_wait > 2000:
            severity = "high"
            
        bottlenecks.append({
            "id": f"queue-delay-{congested_q_name}",
            "title": f"Queue Congestion in '{congested_q_name}'",
            "description": f"Tasks in queue '{congested_q_name}' spent an average of {longest_queue_wait / 1000.0:.2f} seconds waiting to be claimed.",
            "severity": severity,
            "estimated_impact": min(1.0, longest_queue_wait / (pipeline_duration_ms or 1)),
            "affected_duration_ms": longest_queue_wait
        })

    # 1.2 Hottest workers
    hottest_worker = None
    max_utilization = 0.0
    for w in workers:
        util = w.get("utilization") or 0.0
        if util > max_utilization:
            max_utilization = util
            hottest_worker = w.get("worker")
            
    if hottest_worker and max_utilization > 50:
        severity = "medium"
        if max_utilization > 90:
            severity = "critical"
        elif max_utilization > 75:
            severity = "high"
            
        bottlenecks.append({
            "id": f"worker-saturation-{hottest_worker}",
            "title": f"Worker Saturation ({hottest_worker})",
            "description": f"Worker '{hottest_worker}' was active for {max_utilization:.1f}% of the pipeline execution, indicating high load.",
            "severity": severity,
            "estimated_impact": max_utilization / 100.0,
            "affected_duration_ms": int(pipeline_duration_ms * (max_utilization / 100.0))
        })

    # 1.3 Slowest stages
    slowest_stage = None
    max_stage_dur = 0.0
    for stg in stages:
        total_dur = stg.get("total_duration") or 0.0
        if total_dur > max_stage_dur:
            max_stage_dur = total_dur
            slowest_stage = stg.get("stage")
            
    if slowest_stage and max_stage_dur > 100:
        pct = max_stage_dur / (pipeline_duration_ms or 1) * 100
        severity = "low"
        if pct > 40:
            severity = "critical"
        elif pct > 25:
            severity = "high"
            
        bottlenecks.append({
            "id": f"slow-stage-{slowest_stage}",
            "title": f"Slow Stage: {slowest_stage}",
            "description": f"Stage '{slowest_stage}' accounted for {pct:.1f}% of total task execution duration ({max_stage_dur / 1000.0:.2f}s).",
            "severity": severity,
            "estimated_impact": min(1.0, pct / 100.0),
            "affected_duration_ms": max_stage_dur
        })

    # 1.4 Retry hotspots
    retry_hotspot_task = None
    max_retries_for_task = 0
    task_retries = {}
    for seg in timeline:
        t_id = seg.get("task_id")
        retry_idx = seg.get("retry") or 0
        if retry_idx > max_retries_for_task:
            max_retries_for_task = retry_idx
            retry_hotspot_task = t_id
        if retry_idx > 0:
            task_retries[t_id] = task_retries.get(t_id, 0) + 1

    if retry_hotspot_task and max_retries_for_task > 0:
        severity = "medium"
        if max_retries_for_task >= 3:
            severity = "critical"
        elif max_retries_for_task >= 2:
            severity = "high"
            
        bottlenecks.append({
            "id": f"retry-hotspot-task-{retry_hotspot_task}",
            "title": f"Task Retry Hotspot (Task-{retry_hotspot_task})",
            "description": f"Task-{retry_hotspot_task} retried {max_retries_for_task} times, adding latency and resource usage.",
            "severity": severity,
            "estimated_impact": min(1.0, (max_retries_for_task * 500) / (pipeline_duration_ms or 1)),
            "affected_duration_ms": max_retries_for_task * 1000
        })

    # 1.5 Idle workers
    idle_workers = [w.get("worker") for w in workers if w.get("utilization", 0.0) < 15]
    if idle_workers and pipeline_duration_ms > 1000:
        bottlenecks.append({
            "id": "idle-workers",
            "title": f"Underutilized Workers ({len(idle_workers)} detected)",
            "description": f"Workers {', '.join(idle_workers[:3])} had less than 15% utilization, showing potential over-provisioning.",
            "severity": "low",
            "estimated_impact": 0.2,
            "affected_duration_ms": int(pipeline_duration_ms * 0.15)
        })

    # 1.6 Critical path bottlenecks
    cp_list = list(critical_path_tasks)
    if cp_list:
        bottlenecks.append({
            "id": "critical-path-length",
            "title": "Critical Path Dominance",
            "description": f"The critical path contains {len(cp_list)} tasks, taking {critical_path_execution_ms / 1000.0:.2f}s execution and {critical_path_queue_wait_ms / 1000.0:.2f}s wait.",
            "severity": "high" if critical_path_execution_ms / (pipeline_duration_ms or 1) > 0.6 else "medium",
            "estimated_impact": critical_path_execution_ms / (pipeline_duration_ms or 1),
            "affected_duration_ms": int(critical_path_execution_ms + critical_path_queue_wait_ms)
        })

    # 1.7 Longest serial chains
    if len(cp_list) > 3:
        bottlenecks.append({
            "id": "longest-serial-chain",
            "title": "Long Sequential Chain",
            "description": f"A dependency chain of {len(cp_list)} tasks must execute sequentially, limiting maximum speedup.",
            "severity": "high" if len(cp_list) > 6 else "medium",
            "estimated_impact": 0.5,
            "affected_duration_ms": int(critical_path_execution_ms)
        })

    # 1.8 Excessive retries
    excessive_retried_tasks = [tid for tid, count in task_retries.items() if count >= 2]
    if excessive_retried_tasks:
        bottlenecks.append({
            "id": "excessive-retries",
            "title": "Excessive Retries Detected",
            "description": f"Tasks {', '.join(map(str, excessive_retried_tasks[:3]))} experienced 2 or more retries, indicating stability issues.",
            "severity": "high",
            "estimated_impact": 0.4,
            "affected_duration_ms": int(total_retry_duration_ms)
        })

    # 1.9 Starvation
    starved_tasks = []
    for seg in timeline:
        q_w = seg.get("queue_wait_ms") or 0.0
        dur = seg.get("duration_ms") or 0.0
        if q_w > 1000 and q_w > dur * 3:
            starved_tasks.append(seg.get("task_id"))
            
    if starved_tasks:
        bottlenecks.append({
            "id": "worker-starvation",
            "title": "Task Starvation",
            "description": f"Tasks {', '.join(map(str, starved_tasks[:3]))} waited in the queue significantly longer than their execution duration.",
            "severity": "medium",
            "estimated_impact": 0.3,
            "affected_duration_ms": int(sum(seg.get("queue_wait_ms") or 0 for seg in timeline if seg.get("task_id") in starved_tasks))
        })

    # 1.10 Queue Imbalance
    if len(queues) > 1:
        waits = [q.get("metrics", {}).get("mean", 0.0) for q in queues]
        max_w = max(waits)
        min_w = min(waits)
        if max_w - min_w > 1000:
            bottlenecks.append({
                "id": "queue-imbalance",
                "title": "Queue Workload Imbalance",
                "description": f"Queue delays vary significantly between queues, from {min_w/1000.0:.2f}s to {max_w/1000.0:.2f}s.",
                "severity": "medium",
                "estimated_impact": 0.2,
                "affected_duration_ms": int(max_w - min_w)
            })

    # Sort Bottlenecks deterministically
    bottlenecks.sort(key=lambda b: (
        -get_severity_score(b["severity"]),
        -b.get("estimated_impact", 0.0),
        -b.get("affected_duration_ms", 0.0),
        b["id"]
    ))


    # 2. GENERATE DETERMINISTIC RECOMMENDATIONS
    recommendations = []
    
    # Recommendation 2.1: Increase worker pool
    if max_utilization > 75 and worker_count < 6:
        impact = int(critical_path_queue_wait_ms * 0.4)
        recommendations.append({
            "id": f"worker-pool-scaling-{hottest_worker or 'default'}",
            "title": "Increase worker pool size",
            "description": f"Worker utilization is high ({max_utilization:.1f}%). Adding an additional worker would reduce queue wait times.",
            "severity": "high",
            "confidence": "high",
            "estimated_impact_ms": impact,
            "affected_tasks": list(critical_path_tasks),
            "affected_workers": [hottest_worker] if hottest_worker else []
        })

    # Recommendation 2.2: Reduce parser concurrency or split tasks
    if max_stage_dur > 2000 and slowest_stage:
        recommendations.append({
            "id": f"stage-concurrency-reduction-{slowest_stage}",
            "title": f"Reduce concurrency in '{slowest_stage}' stage",
            "description": f"Stage '{slowest_stage}' is causing a large bottleneck. Reducing active concurrency can reduce overhead.",
            "severity": "medium",
            "confidence": "medium",
            "estimated_impact_ms": int(max_stage_dur * 0.15),
            "affected_tasks": [seg.get("task_id") for seg in timeline if seg.get("task_type") == slowest_stage or task_id in critical_path_tasks],
            "affected_workers": []
        })

    # Recommendation 2.3: Split task
    longest_task_id = summary_pm.get("longest_task", {}).get("task_id")
    longest_task_dur = summary_pm.get("longest_task", {}).get("duration_ms") or 0.0
    if longest_task_id and longest_task_dur > 3000:
        recommendations.append({
            "id": f"split-task-{longest_task_id}",
            "title": f"Split Task {longest_task_id}",
            "description": f"Task {longest_task_id} ran for {longest_task_dur/1000.0:.2f}s. Splitting it into smaller, parallel steps would accelerate execution.",
            "severity": "high",
            "confidence": "medium",
            "estimated_impact_ms": int(longest_task_dur * 0.3),
            "affected_tasks": [longest_task_id],
            "affected_workers": []
        })

    # Recommendation 2.4: Reduce retries
    if total_retries > 1:
        recommendations.append({
            "id": "reduce-retries-recommendation",
            "title": "Reduce task retries",
            "description": f"Detected {total_retries} retries in execution. Investigate failures to eliminate recovery overhead.",
            "severity": "high" if total_retries >= 3 else "medium",
            "confidence": "high",
            "estimated_impact_ms": int(total_retry_duration_ms),
            "affected_tasks": list(task_retries.keys()),
            "affected_workers": []
        })

    # Recommendation 2.5: Rebalance priorities or queues
    if len(queues) > 1 and longest_queue_wait > 1000:
        recommendations.append({
            "id": f"queue-rebalance-{congested_q_name or 'default'}",
            "title": "Rebalance queue capacity",
            "description": f"Queue '{congested_q_name}' has significant delays. Dedicate more workers to this queue to stabilize wait times.",
            "severity": "medium",
            "confidence": "high",
            "estimated_impact_ms": int(longest_queue_wait * 0.5),
            "affected_tasks": [seg.get("task_id") for seg in timeline if seg.get("queue") == congested_q_name],
            "affected_workers": []
        })

    # Ensure recommendations sorting is fully deterministic
    recommendations.sort(key=lambda r: (
        -get_severity_score(r["severity"]),
        -r.get("estimated_impact_ms", 0),
        -{"high": 3, "medium": 2, "low": 1}.get(r["confidence"], 1),
        r["title"]
    ))


    # 3. HEATMAPS (Normalized values 0.0 -> 1.0)
    heatmap_workers = []
    for w in workers:
        util = w.get("utilization", 0.0)
        heatmap_workers.append({
            "worker": w.get("worker"),
            "value": round(util / 100.0, 3)
        })
        
    heatmap_queues = []
    # Find max queue wait for normalization
    max_q_mean = max([q.get("metrics", {}).get("mean", 0.0) for q in queues] + [1.0])
    for q in queues:
        mean_wait = q.get("metrics", {}).get("mean", 0.0)
        heatmap_queues.append({
            "queue": q.get("queue"),
            "value": round(min(1.0, mean_wait / max_q_mean), 3)
        })

    heatmap_stages = []
    # Find max stage avg/total duration for normalization
    max_stage_dur_norm = max([s.get("average_duration", 0.0) for s in stages] + [1.0])
    for s in stages:
        avg_dur = s.get("average_duration", 0.0)
        heatmap_stages.append({
            "stage": s.get("stage"),
            "value": round(min(1.0, avg_dur / max_stage_dur_norm), 3)
        })


    # 4. WHAT-IF ANALYSIS BASELINE & COEFFICIENTS
    # We will build coefficients that allow local calculations in the frontend.
    what_if = {
        "assumptions": [
            "identical workload",
            "unchanged DAG",
            "unchanged dependencies",
            "unchanged retry logic",
            "unchanged task durations",
            "only resource parameters vary"
        ],
        "baseline": {
            "pipeline_duration_ms": pipeline_duration_ms,
            "critical_path_duration_ms": summary_pm.get("critical_path_duration_ms") or (critical_path_execution_ms + critical_path_queue_wait_ms),
            "parallel_efficiency": summary_pm.get("parallel_efficiency") or 0.0,
            "total_queue_wait_ms": summary_pm.get("queue_wait_ms") or 0.0,
            "total_execution_ms": summary_pm.get("execution_ms") or 0.0,
            "total_retry_ms": summary_pm.get("retry_ms") or 0.0,
            "worker_count": worker_count,
            "max_concurrency": len(workers) or 1,
            "retry_count": total_retries,
            "critical_path_execution_ms": critical_path_execution_ms,
            "critical_path_queue_wait_ms": critical_path_queue_wait_ms,
            "critical_path_retry_ms": critical_path_retry_ms
        },
        "coefficients": {
            "worker_scaling_factor": 1.0,
            "queue_wait_factor": 1.0,
            "retry_factor": 1.0,
            "parallelism_factor": 1.0
        }
    }

    # 5. METADATA
    metadata = {
        "recommendation_count": len(recommendations),
        "bottleneck_count": len(bottlenecks),
        "simulation_supported": True,
        "generated_from_performance_version": 1
    }

    # 6. OVERALL SCORE & SUMMARY MESSAGE
    score = 100.0
    # deduct score based on bottlenecks
    for b in bottlenecks:
        sev = b["severity"]
        if sev == "critical":
            score -= 15
        elif sev == "high":
            score -= 10
        elif sev == "medium":
            score -= 5
        else:
            score -= 2
    score = max(10.0, min(100.0, score))

    msg = "Execution is optimized with minimal queue delays."
    if bottlenecks:
        top_b = bottlenecks[0]
        msg = f"Potential bottleneck: {top_b['title']}. Review recommendations."

    summary = {
        "overall_score": round(score, 1),
        "message": msg
    }

    return {
        "metadata": metadata,
        "summary": summary,
        "bottlenecks": bottlenecks,
        "recommendations": recommendations,
        "what_if": what_if,
        "heatmaps": {
            "workers": heatmap_workers,
            "queues": heatmap_queues,
            "stages": heatmap_stages
        }
    }
