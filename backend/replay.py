import json
from datetime import datetime
from models import Pipeline, Task, TaskLog, OrchestrationEvent, TaskStatus, PipelineStatus

def build_replay(db, pipeline_id):
    pipeline = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
    if not pipeline:
        return None

    tasks = db.query(Task).filter(Task.pipeline_id == pipeline_id).all()
    task_ids = [t.id for t in tasks]
    task_type_map = {t.id: t.type for t in tasks}

    # Extract correlation_id
    correlation_id = None
    for t in tasks:
        if t.data:
            try:
                d = json.loads(t.data)
                cid = d.get("correlation_id")
                if cid:
                    correlation_id = cid
                    break
            except Exception:
                pass

    # Gather task logs
    task_log_events = []
    if task_ids:
        logs = db.query(TaskLog).filter(TaskLog.task_id.in_(task_ids)).all()
        for log in logs:
            task_obj = next((t for t in tasks if t.id == log.task_id), None)
            cid = correlation_id
            if task_obj and task_obj.data:
                try:
                    task_data = json.loads(task_obj.data)
                    cid = task_data.get("correlation_id") or correlation_id
                except Exception:
                    pass

            # Infer status before/after if possible
            status_before = None
            status_after = None
            if log.event_type == 'task_running':
                status_before = 'queued'
                status_after = 'running'
            elif log.event_type == 'task_completed':
                status_before = 'running'
                status_after = 'completed'
            elif log.event_type == 'task_failed':
                status_before = 'running'
                status_after = 'failed'

            task_log_events.append({
                "_sort_key": (
                    log.created_at or datetime.min,
                    0,  # source priority: task_log = 0
                    log.id
                ),
                "id": f"log-{log.id}",
                "timestamp": log.created_at.isoformat() + "Z" if log.created_at else None,
                "source": "task_log",
                "event_type": log.event_type,
                "pipeline_id": pipeline_id,
                "task_id": log.task_id,
                "task_type": task_type_map.get(log.task_id, "unknown"),
                "worker_id": log.worker_id,
                "correlation_id": cid,
                "status_before": status_before,
                "status_after": status_after,
                "message": log.message,
                "payload": {}
            })

    # Gather orchestration events
    orch_rows = db.query(OrchestrationEvent).filter(OrchestrationEvent.pipeline_id == pipeline_id).all()
    orch_events = []
    for ev in orch_rows:
        cid = ev.correlation_id or correlation_id
        
        status_before = None
        status_after = None
        if ev.event_type == 'task_running' or ev.event_type == 'running':
            status_before = 'queued'
            status_after = 'running'
        elif ev.event_type == 'task_completed' or ev.event_type == 'completed':
            status_before = 'running'
            status_after = 'completed'
        elif ev.event_type == 'task_failed' or ev.event_type == 'failed':
            status_before = 'running'
            status_after = 'failed'

        payload = {}
        if ev.payload_json:
            try:
                payload = json.loads(ev.payload_json) if isinstance(ev.payload_json, str) else ev.payload_json
            except Exception:
                payload = {}

        orch_events.append({
            "_sort_key": (
                ev.created_at or datetime.min,
                1,  # source priority: orchestration_event = 1
                ev.id
            ),
            "id": f"orch-{ev.id}",
            "timestamp": ev.created_at.isoformat() + "Z" if ev.created_at else None,
            "source": "orchestration_event",
            "event_type": ev.event_type,
            "pipeline_id": pipeline_id,
            "task_id": ev.task_id,
            "task_type": task_type_map.get(ev.task_id, "unknown") if ev.task_id else None,
            "worker_id": ev.worker_id,
            "correlation_id": cid,
            "status_before": status_before,
            "status_after": status_after,
            "message": ev.message,
            "payload": payload
        })

    # Merge and sort: timestamp ASC -> source priority -> record ID ASC
    merged = sorted(task_log_events + orch_events, key=lambda e: e["_sort_key"])
    events = [{k: v for k, v in entry.items() if k != "_sort_key"} for entry in merged]

    started_at = pipeline.started_at.isoformat() + "Z" if pipeline.started_at else (events[0]["timestamp"] if events else None)
    finished_at = pipeline.completed_at.isoformat() + "Z" if pipeline.completed_at else (events[-1]["timestamp"] if events else None)

    replay = {
        "version": 1,
        "pipeline_id": pipeline_id,
        "correlation_id": correlation_id,
        "started_at": started_at,
        "finished_at": finished_at,
        "events": events
    }
    return replay


def analyze_execution(replay):
    events = replay.get("events", [])

    first_failure = None
    failed_task_id = None
    failed_task_type = None
    failed_worker_id = None
    failure_message = None

    # Derive first explicit failure, deadlocks, timeouts, manual cancellation
    # Rule precedence: explicit_failure -> dependency_deadlock -> timeout -> worker_lease_expiry -> manual_cancellation
    
    # 1. Check for manual cancellation first (if cancelled by user, it might be the reason, but we check chronologically)
    cancelled_event = next((e for e in events if e["event_type"] in ("pipeline_cancelled", "task_cancelled") or "cancelled" in (e["message"] or "").lower()), None)
    
    # 2. Find first explicit failure event
    failure_event = next((e for e in events if e["status_after"] == "failed" or e["event_type"] in ("task_failed", "failed") or "failed" in (e["message"] or "").lower()), None)

    # 3. Find lease expiry/timeouts
    timeout_event = next((e for e in events if e["event_type"] in ("lease_expired", "timeout") or "lease expired" in (e["message"] or "").lower()), None)

    # Determine match based on rules of precedence
    rule = "unknown"
    confidence = "low"
    root_cause = "No failure detected. Pipeline completed successfully or is in progress."

    if failure_event:
        first_failure = failure_event
        failed_task_id = failure_event.get("task_id")
        failed_task_type = failure_event.get("task_type") or "unknown"
        failed_worker_id = failure_event.get("worker_id") or "unknown"
        failure_message = failure_event.get("message") or "Unknown error"
        rule = "explicit_failure"
        confidence = "high"
        root_cause = f"Task {failed_task_id} ({failed_task_type}) failed on worker {failed_worker_id} with error: '{failure_message}'."
    elif timeout_event:
        first_failure = timeout_event
        failed_task_id = timeout_event.get("task_id")
        failed_task_type = timeout_event.get("task_type") or "unknown"
        failed_worker_id = timeout_event.get("worker_id") or "unknown"
        failure_message = timeout_event.get("message") or "Worker lease expired"
        rule = "worker_lease_expiry"
        confidence = "high"
        root_cause = f"Worker lease expired or task timeout occurred for Task {failed_task_id} ({failed_task_type}) on worker {failed_worker_id}."
    elif cancelled_event:
        first_failure = cancelled_event
        failed_task_id = cancelled_event.get("task_id")
        failed_task_type = cancelled_event.get("task_type") or "unknown"
        failed_worker_id = cancelled_event.get("worker_id") or "system"
        failure_message = cancelled_event.get("message") or "Manual cancellation"
        rule = "manual_cancellation"
        confidence = "high"
        root_cause = f"Pipeline execution was manually cancelled by the user. Action triggered on task: {failed_task_type}."
    
    # Check for deadlocks or circular waiting (e.g. all remaining tasks blocked)
    blocked_events = [e for e in events if e["event_type"] in ("task_blocked", "dependency_blocked")]
    blocked_task_ids = list(set([e["task_id"] for e in blocked_events if e.get("task_id")]))
    
    if len(blocked_task_ids) > 0 and not failure_event and not timeout_event and not cancelled_event:
        rule = "dependency_deadlock"
        confidence = "medium"
        root_cause = f"Pipeline stuck in deadlock: {len(blocked_task_ids)} tasks are blocked on dependencies."

    # Retry chain
    retry_chain = []
    for e in events:
        if e["event_type"] in ("task_recovered", "retry", "task_retry") or "retry" in (e["message"] or "").lower():
            retry_chain.append({
                "timestamp": e["timestamp"],
                "task_id": e.get("task_id"),
                "task_type": e.get("task_type"),
                "worker_id": e.get("worker_id"),
                "message": e["message"]
            })

    # Duration calculation
    duration = 0.0
    if replay.get("started_at") and replay.get("finished_at"):
        try:
            start_dt = datetime.fromisoformat(replay["started_at"].replace("Z", ""))
            end_dt = datetime.fromisoformat(replay["finished_at"].replace("Z", ""))
            duration = (end_dt - start_dt).total_seconds()
        except Exception:
            pass

    # Critical path: trace dependency flow of tasks
    # We can trace task types based on standard flow or events
    critical_path = ["upload", "preprocess_document", "parse_document", "build_graph", "chunk_document", "generate_embeddings", "index_bm25", "query_pipeline", "ready"]

    analysis = {
        "root_cause": root_cause,
        "confidence": confidence,
        "rule": rule,
        "failed_task": {
            "task_id": failed_task_id,
            "task_type": failed_task_type,
            "worker_id": failed_worker_id,
            "error_message": failure_message
        } if failed_task_id else None,
        "retry_chain": retry_chain,
        "blocked_tasks": blocked_task_ids,
        "critical_path": critical_path,
        "duration": duration
    }
    return analysis
