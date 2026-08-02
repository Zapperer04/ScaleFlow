# backend/performance_analysis.py
import json
import math
from datetime import datetime
from critical_path import compute_dag_longest_path

def build_performance_model(replay):
    """
    Builds a deterministic performance model from a Replay object.
    
    Args:
        replay (dict): The replay dictionary containing events and metadata.
        
    Returns:
        dict: The PerformanceModel dictionary conforming to version 1 contract.
    """
    events = replay.get("events", [])
    pipeline_id = replay.get("pipeline_id")
    correlation_id = replay.get("correlation_id")
    
    # 1. Parse timeline segments & track task attempts
    # We trace attempts by task_id. For each attempt, we need:
    # enqueue time, start/claim time, finish/complete/fail time.
    # An attempt is completed or failed.
    task_attempts = {} # task_id -> list of attempt dicts
    # Each attempt dict: { 'enqueue_at': ..., 'started_at': ..., 'finished_at': ..., 'status': ..., 'worker_id': ..., 'queue': ... }
    
    # We also keep track of dependencies from event payloads
    dependencies = {} # child_task_id -> list of parent_task_ids
    task_types = {} # task_id -> task_type
    
    # Track task state transitions to identify attempts
    # Since tasks can retry, we check events chronologically
    for e in events:
        task_id = e.get("task_id")
        if not task_id:
            continue
            
        tid = str(task_id)
        if e.get("task_type"):
            task_types[tid] = e["task_type"]
            
        # Parse dependencies from payload if available
        payload = e.get("payload") or {}
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}
        if "dependencies" in payload:
            dependencies[tid] = [str(x) for x in (payload["dependencies"] or [])]
        elif "task" in payload and isinstance(payload["task"], dict) and "dependencies" in payload["task"]:
            dependencies[tid] = [str(x) for x in (payload["task"]["dependencies"] or [])]
            
        # Initialize attempts list for this task if needed
        if tid not in task_attempts:
            task_attempts[tid] = []
            
        event_type = e.get("event_type") or ""
        msg = (e.get("message") or "").lower()
        worker = e.get("worker_id") or "system"
        queue = e.get("payload", {}).get("queue") or e.get("payload", {}).get("queue_name") or "default" if isinstance(e.get("payload"), dict) else "default"
        
        # Determine if we should create a new attempt
        is_new_attempt_event = event_type in ("task_queued", "task_retry", "task_recovered") or "retry" in msg or not task_attempts[tid]
        
        if is_new_attempt_event:
            # If the last attempt is already unfinished and this is a retry/queue event, mark the last one finished (failed) first
            if task_attempts[tid] and task_attempts[tid][-1].get("finished_at") is None:
                task_attempts[tid][-1]["finished_at"] = e.get("timestamp")
                task_attempts[tid][-1]["status"] = "failed"
                
            task_attempts[tid].append({
                "enqueue_at": e.get("timestamp"),
                "started_at": None,
                "finished_at": None,
                "status": "pending",
                "worker_id": worker,
                "queue": queue
            })
            
        current_attempt = task_attempts[tid][-1]
        
        # Now apply status updates based on the current event
        if event_type in ("task_running", "running") or e.get("status_after") == "running":
            if current_attempt.get("started_at") is None:
                current_attempt["started_at"] = e.get("timestamp")
            current_attempt["status"] = "running"
            if worker and worker != "system":
                current_attempt["worker_id"] = worker
                
        elif event_type in ("task_completed", "completed") or e.get("status_after") == "completed":
            if current_attempt.get("started_at") is None:
                current_attempt["started_at"] = e.get("timestamp") # Fallback
            current_attempt["finished_at"] = e.get("timestamp")
            current_attempt["status"] = "completed"
            if worker and worker != "system":
                current_attempt["worker_id"] = worker
                
        elif event_type in ("task_failed", "failed") or e.get("status_after") == "failed":
            if current_attempt.get("started_at") is None:
                current_attempt["started_at"] = e.get("timestamp") # Fallback
            current_attempt["finished_at"] = e.get("timestamp")
            current_attempt["status"] = "failed"
            if worker and worker != "system":
                current_attempt["worker_id"] = worker

    # Determine pipeline start time
    pipeline_start = None
    if replay.get("started_at"):
        try:
            pipeline_start = datetime.fromisoformat(replay["started_at"].replace("Z", ""))
        except Exception:
            pass
            
    if not pipeline_start and events:
        for e in events:
            if e.get("timestamp"):
                try:
                    pipeline_start = datetime.fromisoformat(e["timestamp"].replace("Z", ""))
                    break
                except Exception:
                    pass

    def get_relative_ms(ts_str):
        if not pipeline_start or not ts_str:
            return 0
        try:
            dt = datetime.fromisoformat(ts_str.replace("Z", ""))
            return int((dt - pipeline_start).total_seconds() * 1000)
        except Exception:
            return 0

    # Build timeline segments
    timeline = []
    for tid, attempts in task_attempts.items():
        for retry_idx, att in enumerate(attempts):
            started_at = att.get("started_at")
            finished_at = att.get("finished_at") or att.get("started_at") # Fallback if unfinished
            
            # Queue wait computation: enqueue -> start
            queue_wait_ms = None
            if att.get("enqueue_at") and started_at:
                try:
                    enq_dt = datetime.fromisoformat(att["enqueue_at"].replace("Z", ""))
                    str_dt = datetime.fromisoformat(started_at.replace("Z", ""))
                    diff = (str_dt - enq_dt).total_seconds() * 1000
                    queue_wait_ms = max(0, int(diff))
                except Exception:
                    pass
            
            start_ms = get_relative_ms(started_at)
            end_ms = get_relative_ms(finished_at)
            duration_ms = max(0, end_ms - start_ms)
            
            timeline.append({
                "segment_id": f"task-{tid}-attempt-{retry_idx}",
                "task_id": int(tid) if tid.isdigit() else tid,
                "task_type": task_types.get(tid, "unknown"),
                "worker_id": att.get("worker_id") or "unknown",
                "queue": att.get("queue") or "default",
                "started_at": started_at,
                "finished_at": finished_at,
                "start_ms": start_ms,
                "end_ms": end_ms,
                "duration_ms": duration_ms,
                "queue_wait_ms": queue_wait_ms,
                "retry": retry_idx,
                "status": att.get("status") or "completed"
            })

    # Timeline sorted deterministically: start_ms -> duration_ms -> segment_id
    timeline = sorted(timeline, key=lambda x: (x["start_ms"], x["duration_ms"], x["segment_id"]))

    # 2. Extract immutable lanes lookup table (Workers sorted alphabetically)
    workers_set = set()
    for seg in timeline:
        if seg["worker_id"] and seg["worker_id"] != "system":
            workers_set.add(seg["worker_id"])
    sorted_workers = sorted(list(workers_set))
    
    lanes = [{"lane": idx, "worker_id": w} for idx, w in enumerate(sorted_workers)]
    worker_lane_map = {w: idx for idx, w in enumerate(sorted_workers)}
    
    # Assign lane index to each segment
    for seg in timeline:
        seg["lane"] = worker_lane_map.get(seg["worker_id"], 0)

    # Pipeline total duration
    pipeline_duration_ms = 0
    if events:
        try:
            first_ts = events[0].get("timestamp")
            last_ts = events[-1].get("timestamp")
            if first_ts and last_ts:
                f_dt = datetime.fromisoformat(first_ts.replace("Z", ""))
                l_dt = datetime.fromisoformat(last_ts.replace("Z", ""))
                pipeline_duration_ms = max(0, int((l_dt - f_dt).total_seconds() * 1000))
        except Exception:
            pass
            
    if pipeline_duration_ms == 0 and replay.get("metadata", {}).get("duration"):
        pipeline_duration_ms = int(replay["metadata"]["duration"] * 1000)

    # 3. Worker utilization calculations
    workers_metrics = []
    # Calculate lease expired events count per worker
    lease_expiries = {}
    for e in events:
        if e.get("event_type") == "lease_expired" and e.get("worker_id"):
            w = e["worker_id"]
            lease_expiries[w] = lease_expiries.get(w, 0) + 1

    for w in sorted_workers:
        w_segs = [s for s in timeline if s["worker_id"] == w]
        busy_ms = sum(s["duration_ms"] for s in w_segs)
        idle_ms = max(0, pipeline_duration_ms - busy_ms)
        utilization = round((busy_ms / pipeline_duration_ms * 100), 2) if pipeline_duration_ms > 0 else 0.0
        
        tasks_completed = sum(1 for s in w_segs if s["status"] == "completed")
        tasks_failed = sum(1 for s in w_segs if s["status"] == "failed")
        retries = sum(1 for s in w_segs if s["retry"] > 0)
        
        workers_metrics.append({
            "worker": w,
            "utilization": utilization,
            "busy_ms": busy_ms,
            "idle_ms": idle_ms,
            "tasks": len(set(s["task_id"] for s in w_segs)),
            "tasks_completed": tasks_completed,
            "tasks_failed": tasks_failed,
            "retry_count": retries,
            "lease_expiry_count": lease_expiries.get(w, 0)
        })
    # Sort workers utilization DESC -> busy_ms DESC -> worker ID ASC
    workers_metrics = sorted(workers_metrics, key=lambda x: (-x["utilization"], -x["busy_ms"], x["worker"]))

    # Helper stats function
    def compute_stats(samples):
        if not samples:
            return {
                "count": 0,
                "missing": 0,
                "min": 0,
                "max": 0,
                "mean": 0,
                "median": 0,
                "p95": 0,
                "p99": 0,
                "std_dev": 0
            }
        
        valid_samples = [s for s in samples if s is not None]
        missing_count = len(samples) - len(valid_samples)
        
        if not valid_samples:
            return {
                "count": 0,
                "missing": missing_count,
                "min": 0,
                "max": 0,
                "mean": 0,
                "median": 0,
                "p95": 0,
                "p99": 0,
                "std_dev": 0
            }
            
        sorted_s = sorted(valid_samples)
        n = len(sorted_s)
        
        min_v = sorted_s[0]
        max_v = sorted_s[-1]
        mean_v = sum(sorted_s) / n
        
        if n % 2 == 1:
            median_v = sorted_s[n // 2]
        else:
            median_v = (sorted_s[n // 2 - 1] + sorted_s[n // 2]) / 2.0
            
        def percentile(p):
            k = (n - 1) * (p / 100.0)
            f = math.floor(k)
            c = math.ceil(k)
            if f == c:
                return sorted_s[int(k)]
            return sorted_s[f] * (c - k) + sorted_s[c] * (k - f)
            
        p95_v = percentile(95)
        p99_v = percentile(99)
        
        variance = sum((x - mean_v) ** 2 for x in sorted_s) / n
        std_dev_v = math.sqrt(variance)
        
        return {
            "count": n,
            "missing": missing_count,
            "min": round(min_v, 2),
            "max": round(max_v, 2),
            "mean": round(mean_v, 2),
            "median": round(median_v, 2),
            "p95": round(p95_v, 2),
            "p99": round(p99_v, 2),
            "std_dev": round(std_dev_v, 2)
        }

    # 4. Queue Delay Analysis
    queues_map = {}
    for seg in timeline:
        q = seg["queue"]
        if q not in queues_map:
            queues_map[q] = []
        queues_map[q].append(seg["queue_wait_ms"])
        
    queues_metrics = []
    for q, waits in queues_map.items():
        stats = compute_stats(waits)
        queues_metrics.append({
            "queue": q,
            "metrics": stats
        })

    # 5. Stage Analysis (aggregated by task type)
    stage_groups = {}
    for seg in timeline:
        stg = task_types.get(str(seg["task_id"]), "unknown")
        if stg not in stage_groups:
            stage_groups[stg] = []
        stage_groups[stg].append(seg)
        
    stages_metrics = []
    for stg, segs in stage_groups.items():
        durations = [s["duration_ms"] for s in segs]
        stats = compute_stats(durations)
        
        # slowest / fastest task
        slowest_seg = max(segs, key=lambda s: s["duration_ms"])
        fastest_seg = min(segs, key=lambda s: s["duration_ms"])
        
        stages_metrics.append({
            "stage": stg,
            "count": stats["count"],
            "total_duration": sum(durations),
            "average_duration": stats["mean"],
            "median_duration": stats["median"],
            "p95_duration": stats["p95"],
            "slowest_task": {
                "task_id": slowest_seg["task_id"],
                "duration_ms": slowest_seg["duration_ms"]
            },
            "fastest_task": {
                "task_id": fastest_seg["task_id"],
                "duration_ms": fastest_seg["duration_ms"]
            }
        })
    # Default sorting: Total Duration DESC
    stages_metrics = sorted(stages_metrics, key=lambda x: -x["total_duration"])

    # 6. Critical Path
    # Reconstruct DAG
    task_ids = list(task_attempts.keys())
    adj = {tid: [] for tid in task_ids}
    in_degree = {tid: 0 for tid in task_ids}
    
    # If there are no dependencies captured in payloads, fall back to standard sequence
    has_deps = False
    for child, parents in dependencies.items():
        if parents:
            has_deps = True
            
    if not has_deps and len(task_ids) > 1:
        # Fallback sequence dependencies based on start time order
        sorted_tids_by_start = [str(x["task_id"]) for x in timeline if x["retry"] == 0]
        # De-duplicate while preserving order
        seen = set()
        flow_seq = []
        for tid in sorted_tids_by_start:
            if tid not in seen:
                seen.add(tid)
                flow_seq.append(tid)
        # Create consecutive dependencies
        for i in range(len(flow_seq) - 1):
            dependencies[flow_seq[i+1]] = [flow_seq[i]]
            
    # Populate adjacency and in_degrees
    for child, parents in dependencies.items():
        child_str = str(child)
        if child_str not in in_degree:
            continue
        for p in parents:
            parent_str = str(p)
            if parent_str in adj:
                adj[parent_str].append(child_str)
                in_degree[child_str] += 1

    # Weights for DP: sum of execution and queue waits for attempts
    weights = {}
    for tid in task_ids:
        # Sum duration and queue waits of all retries for this task
        t_segs = [s for s in timeline if str(s["task_id"]) == tid]
        exec_dur = sum(s["duration_ms"] for s in t_segs)
        q_wait = sum((s["queue_wait_ms"] or 0) for s in t_segs)
        weights[tid] = {
            "total": float(exec_dur + q_wait)
        }

    critical_path_tasks_str, critical_path_edges_str = compute_dag_longest_path(
        task_ids, adj, in_degree, weights
    )
    
    # Convert string IDs back to integer if applicable
    def to_original_id(s):
        return int(s) if s.isdigit() else s
        
    critical_path_tasks = [to_original_id(x) for x in critical_path_tasks_str]
    critical_path_edges = [[to_original_id(e[0]), to_original_id(e[1])] for e in critical_path_edges_str]

    # Calculate critical path duration in ms
    critical_path_duration = 0.0
    for tid in critical_path_tasks_str:
        critical_path_duration += weights[tid]["total"]

    # 7. Flame Graph Spans
    # Deterministic hierarchical flame graph spans
    flamegraph = []
    # Build tree depths from topological order or dependencies
    # For now, depth is determined by the number of parents in dependency chain
    depths = {}
    def get_depth(tid):
        if tid in depths:
            return depths[tid]
        parents = dependencies.get(tid, [])
        if not parents:
            depths[tid] = 0
            return 0
        max_p_depth = -1
        for p in parents:
            if str(p) != tid: # Avoid self-cycle
                max_p_depth = max(max_p_depth, get_depth(str(p)))
        depths[tid] = max_p_depth + 1
        return depths[tid]

    for tid in task_ids:
        get_depth(tid)

    for seg in timeline:
        tid = str(seg["task_id"])
        parents = dependencies.get(tid, [])
        parent_task_id = to_original_id(parents[0]) if parents else None
        
        flamegraph.append({
            "task_id": seg["task_id"],
            "parent_task_id": parent_task_id,
            "depth": depths.get(tid, 0),
            "start_ms": seg["start_ms"],
            "duration_ms": seg["duration_ms"],
            "status": seg["status"],
            "worker_id": seg["worker_id"]
        })
    # Sorted deterministically: start_ms ASC -> depth ASC -> duration_ms DESC -> task_id ASC
    flamegraph = sorted(flamegraph, key=lambda x: (x["start_ms"], x["depth"], -x["duration_ms"], str(x["task_id"])))

    # 8. Summary statistics
    all_queue_waits = [s["queue_wait_ms"] for s in timeline if s["queue_wait_ms"] is not None]
    all_executions = [s["duration_ms"] for s in timeline]
    all_retries_durations = [s["duration_ms"] for s in timeline if s["retry"] > 0]
    
    total_queue_wait = sum(all_queue_waits)
    total_execution = sum(all_executions)
    total_retry = sum(all_retries_durations)
    
    # Calculate idle time across workers
    total_worker_idle = sum(w["idle_ms"] for w in workers_metrics)
    
    # Bounded parallel efficiency: Critical Path Duration / Pipeline Duration
    parallel_efficiency = round((critical_path_duration / pipeline_duration_ms), 4) if pipeline_duration_ms > 0 else 0.0

    longest_task = max(timeline, key=lambda s: s["duration_ms"]) if timeline else None
    slowest_worker = max(workers_metrics, key=lambda w: w["utilization"]) if workers_metrics else None
    
    most_congested_q = None
    max_mean_wait = -1
    for q_m in queues_metrics:
        mean_wait = q_m["metrics"]["mean"]
        if mean_wait > max_mean_wait:
            max_mean_wait = mean_wait
            most_congested_q = q_m["queue"]

    summary = {
        "pipeline_duration_ms": pipeline_duration_ms,
        "critical_path_duration_ms": critical_path_duration,
        "critical_path_percentage": round((critical_path_duration / pipeline_duration_ms * 100), 2) if pipeline_duration_ms > 0 else 0.0,
        "queue_wait_ms": total_queue_wait,
        "queue_wait_percentage": round((total_queue_wait / (pipeline_duration_ms or 1) * 100), 2),
        "execution_ms": total_execution,
        "execution_percentage": round((total_execution / (pipeline_duration_ms or 1) * 100), 2),
        "retry_ms": total_retry,
        "retry_percentage": round((total_retry / (pipeline_duration_ms or 1) * 100), 2),
        "idle_ms": total_worker_idle,
        "idle_percentage": round((total_worker_idle / ((pipeline_duration_ms * len(sorted_workers)) or 1) * 100), 2) if sorted_workers else 0.0,
        "parallel_efficiency": parallel_efficiency,
        "longest_task": {
            "task_id": longest_task["task_id"] if longest_task else None,
            "duration_ms": longest_task["duration_ms"] if longest_task else 0
        },
        "slowest_worker": slowest_worker["worker"] if slowest_worker else None,
        "most_congested_queue": most_congested_q,
        "worker_count": len(sorted_workers),
        "task_count": len(task_ids)
    }

    # 9. Overall Statistics
    statistics = {
        "queue_wait": compute_stats(all_queue_waits),
        "execution": compute_stats(all_executions),
        "pipeline": {
            "count": 1,
            "min": pipeline_duration_ms,
            "max": pipeline_duration_ms,
            "mean": pipeline_duration_ms,
            "median": pipeline_duration_ms,
            "p95": pipeline_duration_ms,
            "p99": pipeline_duration_ms,
            "std_dev": 0
        },
        "retries": compute_stats(all_retries_durations)
    }

    return {
        "summary": summary,
        "critical_path": {
            "tasks": critical_path_tasks,
            "edges": critical_path_edges
        },
        "timeline": timeline,
        "lanes": lanes,
        "workers": workers_metrics,
        "queues": queues_metrics,
        "stages": stages_metrics,
        "flamegraph": flamegraph,
        "statistics": statistics
    }
