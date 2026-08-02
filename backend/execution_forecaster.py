# backend/execution_forecaster.py
import math
from datetime import datetime, timedelta

def build_execution_forecast(performance_model, optimization_model, sla_ms=None):
    """
    Builds a ForecastModel by consuming only the PerformanceModel and OptimizationModel.
    Ensures zero database queries, zero event parsing, and strictly deterministic output.
    """
    if not performance_model or not isinstance(performance_model, dict):
        performance_model = {}
    if not optimization_model or not isinstance(optimization_model, dict):
        optimization_model = {}

    summary_pm = performance_model.get("summary") or {}
    timeline = performance_model.get("timeline") or []
    stages = performance_model.get("stages") or []
    workers = performance_model.get("workers") or []
    queues = performance_model.get("queues") or []
    critical_path = performance_model.get("critical_path") or {}
    critical_path_tasks = set(critical_path.get("tasks") or [])

    pipeline_duration_ms = summary_pm.get("pipeline_duration_ms") or 0

    # 1. Parse pipeline start
    start_dates = []
    for seg in timeline:
        for field in ("started_at", "enqueue_at"):
            if seg.get(field):
                try:
                    dt = datetime.fromisoformat(seg[field].replace("Z", ""))
                    start_dates.append(dt)
                except Exception:
                    pass
    pipeline_start_dt = min(start_dates) if start_dates else datetime.utcnow()

    # 2. Map task states
    all_tids = set()
    completed_tids = set()
    running_tids = set()
    failed_tids = set()
    pending_tids = set()

    task_segments = {}
    task_types = {}
    for s in timeline:
        tid = s["task_id"]
        all_tids.add(tid)
        task_segments.setdefault(tid, []).append(s)
        if s.get("task_type"):
            task_types[tid] = s["task_type"]

    for tid in critical_path_tasks:
        all_tids.add(tid)

    for tid in all_tids:
        segs = task_segments.get(tid, [])
        if not segs:
            pending_tids.add(tid)
            continue
        statuses = [s["status"] for s in segs]
        if "completed" in statuses:
            completed_tids.add(tid)
        elif "running" in statuses:
            running_tids.add(tid)
        elif "failed" in statuses:
            failed_tids.add(tid)
        else:
            pending_tids.add(tid)

    # 3. Calculate current playhead
    completed_ends = [s["end_ms"] for s in timeline if s["status"] == "completed"]
    running_starts = [s["start_ms"] for s in timeline if s["status"] == "running"]
    current_ms = max(completed_ends + running_starts) if (completed_ends + running_starts) else 0

    # 4. Reconstruct DAG dependencies from flamegraph
    dependencies = {}
    for item in performance_model.get("flamegraph", []):
        child = item["task_id"]
        parent = item.get("parent_task_id")
        if parent is not None:
            dependencies.setdefault(child, []).append(parent)

    # Topological sorting of all tasks
    tasks_to_schedule = list(all_tids)
    adj = {tid: [] for tid in tasks_to_schedule}
    in_degree = {tid: 0 for tid in tasks_to_schedule}
    for child, parents in dependencies.items():
        if child not in in_degree:
            continue
        for p in parents:
            if p in adj:
                adj[p].append(child)
                in_degree[child] += 1

    # Topological sorting queue
    queue = [tid for tid in tasks_to_schedule if in_degree[tid] == 0]
    topo_order = []
    while queue:
        queue.sort(key=str)
        curr = queue.pop(0)
        topo_order.append(curr)
        for child in adj[curr]:
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

    # Fallback to handle remaining tasks not captured by dependencies
    remaining_tasks = sorted([t for t in tasks_to_schedule if t not in topo_order], key=str)
    topo_order.extend(remaining_tasks)

    # 5. Extract stage averages & retry rates
    stage_avg_duration = {}
    stage_avg_queue_wait = {}
    stage_retry_overhead = {}

    for stg in stages:
        name = stg["stage"]
        stage_avg_duration[name] = stg.get("average_duration") or 1000.0
        
        # Calculate queue wait
        segs = [s for s in timeline if s.get("task_type") == name]
        waits = [s["queue_wait_ms"] for s in segs if s.get("queue_wait_ms") is not None]
        stage_avg_queue_wait[name] = (sum(waits) / len(waits)) if waits else 0.0
        
        # Calculate retry overhead
        unique_tasks = len(set(s["task_id"] for s in segs))
        total_attempts = len(segs)
        retry_rate = (total_attempts - unique_tasks) / unique_tasks if unique_tasks > 0 else 0.0
        stage_retry_overhead[name] = retry_rate * stage_avg_duration[name]

    # 6. Predict future timings
    predicted_start = {}
    predicted_end = {}

    for tid in topo_order:
        parents = [p for p in dependencies.get(tid, []) if p in predicted_end]
        stg_name = task_types.get(tid, "unknown")
        
        expected_dur = stage_avg_duration.get(stg_name, 1000.0)
        expected_q = stage_avg_queue_wait.get(stg_name, 0.0)
        expected_ret = stage_retry_overhead.get(stg_name, 0.0)

        task_segs = task_segments.get(tid, [])
        comp_seg = next((s for s in task_segs if s["status"] == "completed"), None)
        run_seg = next((s for s in task_segs if s["status"] == "running"), None)

        if comp_seg:
            predicted_start[tid] = comp_seg["start_ms"]
            predicted_end[tid] = comp_seg["end_ms"]
        elif run_seg:
            predicted_start[tid] = run_seg["start_ms"]
            elapsed = current_ms - run_seg["start_ms"]
            remaining = max(0.0, expected_dur - elapsed)
            predicted_end[tid] = current_ms + remaining
        else:
            if parents:
                parent_end = max(predicted_end[p] for p in parents)
            else:
                parent_end = current_ms
            predicted_start[tid] = parent_end + expected_q
            predicted_end[tid] = predicted_start[tid] + expected_dur + expected_ret

    # 7. Check if pipeline is completed
    is_completed = len(completed_tids) == len(all_tids) and len(all_tids) > 0
    if not all_tids:
        is_completed = True

    if is_completed:
        remaining_duration_ms = 0.0
        estimated_finish = (pipeline_start_dt + timedelta(milliseconds=pipeline_duration_ms)).isoformat() + "Z"
        progress = 100.0
        critical_path_remaining_ms = 0.0
        queue_wait_remaining_ms = 0.0
        retry_remaining_ms = 0.0
    else:
        estimated_pipeline_duration_ms = max(predicted_end.values()) if predicted_end else 0.0
        remaining_duration_ms = max(0.0, estimated_pipeline_duration_ms - current_ms)
        estimated_finish = (pipeline_start_dt + timedelta(milliseconds=estimated_pipeline_duration_ms)).isoformat() + "Z"
        progress = round((len(completed_tids) / len(all_tids)) * 100, 2) if all_tids else 0.0

        # Remaining Critical Path
        critical_path_remaining_ms = 0.0
        for tid in critical_path_tasks:
            if tid in completed_tids:
                continue
            if tid in running_tids:
                run_seg = next(s for s in task_segments[tid] if s["status"] == "running")
                stg_name = task_types.get(tid, "unknown")
                expected_dur = stage_avg_duration.get(stg_name, 1000.0)
                elapsed = current_ms - run_seg["start_ms"]
                critical_path_remaining_ms += max(0.0, expected_dur - elapsed)
            else:
                stg_name = task_types.get(tid, "unknown")
                expected_dur = stage_avg_duration.get(stg_name, 1000.0)
                expected_q = stage_avg_queue_wait.get(stg_name, 0.0)
                expected_ret = stage_retry_overhead.get(stg_name, 0.0)
                critical_path_remaining_ms += (expected_dur + expected_q + expected_ret)

        queue_wait_remaining_ms = sum(stage_avg_queue_wait.get(task_types.get(tid, "unknown"), 0.0) for tid in pending_tids)
        retry_remaining_ms = sum(stage_retry_overhead.get(task_types.get(tid, "unknown"), 0.0) for tid in pending_tids)

    # 8. SLA analysis
    # Use provided SLA or default to historical duration / 30s
    total_predicted_duration_ms = current_ms + remaining_duration_ms
    if sla_ms is None:
        sla_ms = pipeline_duration_ms if pipeline_duration_ms > 0 else 30000.0

    remaining_buffer = max(0.0, sla_ms - total_predicted_duration_ms)
    expected_overrun = max(0.0, total_predicted_duration_ms - sla_ms)

    if total_predicted_duration_ms > sla_ms:
        if current_ms > sla_ms:
            sla_status = "Missed"
        else:
            sla_status = "Likely Miss"
    else:
        buffer_pct = (remaining_buffer / sla_ms) * 100 if sla_ms > 0 else 0
        if buffer_pct > 20:
            sla_status = "On Track"
        elif buffer_pct >= 5:
            sla_status = "At Risk"
        else:
            sla_status = "Likely Miss"

    # 9. Confidence Level
    completion_pct = progress
    retry_volatility = (sum(s.get("retry", 0) for s in timeline) / len(all_tids)) if all_tids else 0.0
    
    max_mean_queue = 0.0
    for q in queues:
        metrics = q.get("metrics") or {}
        max_mean_queue = max(max_mean_queue, metrics.get("mean") or 0.0)

    lease_expiries = sum(w.get("lease_expiry_count", 0) for w in workers)

    confidence_score = 100
    if completion_pct < 30:
        confidence_score -= 20
    elif completion_pct < 60:
        confidence_score -= 10
    
    if retry_volatility > 0.2:
        confidence_score -= 15
    if max_mean_queue > 2000:
        confidence_score -= 15
    if lease_expiries > 0:
        confidence_score -= 10

    if confidence_score >= 75:
        confidence = "High"
    elif confidence_score >= 45:
        confidence = "Medium"
    else:
        confidence = "Low"

    # 10. Worker forecasts
    worker_forecasts = []
    for w_metrics in workers:
        w_id = w_metrics["worker"]
        # Filter segments for this worker
        w_segs = [s for s in timeline if s["worker_id"] == w_id]
        completed_busy = sum(s["duration_ms"] for s in w_segs if s["status"] == "completed")
        
        # Check running
        run_seg = next((s for s in w_segs if s["status"] == "running"), None)
        running_busy = 0.0
        if run_seg:
            stg = task_types.get(run_seg["task_id"], "unknown")
            expected_dur = stage_avg_duration.get(stg, 1000.0)
            elapsed = current_ms - run_seg["start_ms"]
            running_busy = elapsed + max(0.0, expected_dur - elapsed)

        # Worker predicted busy includes completed + running busy
        predicted_busy_ms = completed_busy + running_busy
        
        # Find likely worker finish
        worker_task_ends = [predicted_end[s["task_id"]] for s in w_segs if s["task_id"] in predicted_end]
        likely_finish_ms = max(worker_task_ends) if worker_task_ends else current_ms

        total_dur = max(total_predicted_duration_ms, 1.0)
        predicted_util = round((predicted_busy_ms / total_dur) * 100, 2)

        worker_forecasts.append({
            "worker": w_id,
            "current_utilization": w_metrics.get("utilization") or 0.0,
            "predicted_utilization": predicted_util,
            "likely_finish_ms": likely_finish_ms,
            "likely_finish": (pipeline_start_dt + timedelta(milliseconds=likely_finish_ms)).isoformat() + "Z"
        })

    # Sort worker forecasts: 1. predicted_finish_ms (likely_finish_ms) DESC, 2. worker_id ASC
    worker_forecasts = sorted(worker_forecasts, key=lambda x: (-x["likely_finish_ms"], x["worker"]))

    # 11. Stage forecasts
    stage_forecasts = []
    # Identify stages from timeline and critical path tasks
    all_stages = set(stg["stage"] for stg in stages)
    for seg in timeline:
        if seg.get("task_type"):
            all_stages.add(seg["task_type"])
    for tid in critical_path_tasks:
        if tid in task_types:
            all_stages.add(task_types[tid])

    for stg_name in all_stages:
        stg_tids = [tid for tid, ttype in task_types.items() if ttype == stg_name]
        if not stg_tids:
            continue
        
        stg_completed = [t for t in stg_tids if t in completed_tids]
        stg_progress = round((len(stg_completed) / len(stg_tids)) * 100, 2) if stg_tids else 0.0
        
        # Remaining duration for this stage
        stg_remaining_duration = 0.0
        stg_task_ends = []
        for tid in stg_tids:
            if tid in completed_tids:
                stg_task_ends.append(predicted_end[tid])
                continue
            if tid in running_tids:
                run_seg = next(s for s in task_segments[tid] if s["status"] == "running")
                expected_dur = stage_avg_duration.get(stg_name, 1000.0)
                elapsed = current_ms - run_seg["start_ms"]
                rem = max(0.0, expected_dur - elapsed)
                stg_remaining_duration += rem
            else:
                expected_dur = stage_avg_duration.get(stg_name, 1000.0)
                expected_q = stage_avg_queue_wait.get(stg_name, 0.0)
                expected_ret = stage_retry_overhead.get(stg_name, 0.0)
                stg_remaining_duration += (expected_dur + expected_q + expected_ret)
            
            if tid in predicted_end:
                stg_task_ends.append(predicted_end[tid])

        eta_ms = max(stg_task_ends) if stg_task_ends else current_ms
        eta_iso = (pipeline_start_dt + timedelta(milliseconds=eta_ms)).isoformat() + "Z"

        # Determine if stage has tasks on critical path
        is_cp_stage = any(tid in critical_path_tasks for tid in stg_tids)

        stage_forecasts.append({
            "stage": stg_name,
            "progress": stg_progress,
            "remaining_ms": stg_remaining_duration,
            "eta": eta_iso,
            "confidence": confidence,
            "is_critical": is_cp_stage
        })

    # Sort stage forecasts: 1. critical path stage first, 2. remaining duration DESC, 3. stage name ASC
    stage_forecasts = sorted(stage_forecasts, key=lambda x: (0 if x["is_critical"] else 1, -x["remaining_ms"], x["stage"]))

    # 12. Remaining Critical Path
    cp_completed_tasks = list(completed_tids & critical_path_tasks)
    cp_remaining_tasks = list(critical_path_tasks - completed_tids)
    
    # Sort critical path tasks by predicted start time
    cp_completed_tasks = sorted(cp_completed_tasks, key=lambda tid: predicted_start.get(tid, 0))
    cp_remaining_tasks = sorted(cp_remaining_tasks, key=lambda tid: predicted_start.get(tid, 0))

    # 13. Future execution segments (for timeline dashed segments overlay)
    future_tasks = []
    for tid in topo_order:
        if tid not in completed_tids:
            future_tasks.append({
                "task_id": tid,
                "task_type": task_types.get(tid, "unknown"),
                "predicted_start_ms": predicted_start[tid],
                "predicted_end_ms": predicted_end[tid],
                "predicted_duration_ms": predicted_end[tid] - predicted_start[tid],
                "status": "running" if tid in running_tids else "pending",
                "is_critical": tid in critical_path_tasks
            })

    # Find bottleneck
    current_bottleneck = "None"
    for b in optimization_model.get("bottlenecks", []):
        if b.get("severity") in ("critical", "high"):
            current_bottleneck = b.get("title")
            break

    # Build predictions metadata
    metadata = {
        "generated_from_performance_version": 1,
        "generated_from_optimization_version": 1,
        "prediction_method": "deterministic-heuristic-v1",
        "completed_tasks": len(completed_tids),
        "remaining_tasks": len(pending_tids) + len(running_tids)
    }

    forecast = {
        "remaining_duration_ms": remaining_duration_ms,
        "estimated_finish": estimated_finish,
        "progress": progress,
        "critical_path_remaining_ms": critical_path_remaining_ms,
        "queue_wait_remaining_ms": queue_wait_remaining_ms,
        "retry_remaining_ms": retry_remaining_ms,
        "worker_forecasts": worker_forecasts,
        "stage_forecasts": stage_forecasts,
        "sla_status": sla_status,
        "confidence": confidence,
        "remaining_buffer": remaining_buffer,
        "expected_overrun": expected_overrun,
        "critical_path": {
            "completed_tasks": cp_completed_tasks,
            "remaining_tasks": cp_remaining_tasks,
            "remaining_duration_ms": critical_path_remaining_ms
        },
        "future_tasks": future_tasks,
        "current_bottleneck": current_bottleneck,
        "metadata": metadata
    }

    return forecast
