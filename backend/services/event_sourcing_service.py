import json
import gzip
import logging
from collections import deque
from datetime import datetime, timedelta
from sqlalchemy import text, and_, or_
from models import OrchestrationEvent, OrchestrationSnapshot, Pipeline, Task, Artifact

logger = logging.getLogger(__name__)

# Canonical Categorization Map
EVENT_CATEGORIES = {
    # Critical: Key lifecycle changes
    "PIPELINE_CREATED": "critical",
    "PIPELINE_COMPLETED": "critical",
    "PIPELINE_FAILED": "critical",
    "TASK_CREATED": "critical",
    "TASK_COMPLETED": "critical",
    "TASK_FAILED": "critical",
    "PIPELINE_OWNERSHIP_TAKEN_OVER": "critical",
    
    # Operational: Execution state changes, lease management, and recoveries
    "TASK_QUEUED": "operational",
    "TASK_CLAIMED": "operational",
    "LEASE_RENEWED": "operational",
    "LEASE_EXPIRED": "operational",
    "TASK_STARTED": "operational",
    "TASK_RECOVERED": "operational",
    "TASK_BLOCKED": "operational",
    "TASK_RELEASED": "operational",
    "BACKPRESSURE_DEFERRED": "operational",
    
    # Telemetry: Queue forecasts, metrics updates
    "QUEUE_PRESSURE_UPDATE": "telemetry",
    "THROUGHPUT_UPDATE": "telemetry",
    
    # Debug: Verbose system diagnostics
    "STALE_WORKER_UPDATE_REJECTED": "debug",
    "PRIORITY_ESCALATED": "debug",
    "ARTIFACT_CREATED": "debug",
    "DEPENDENCY_RELEASED": "debug",
    "DEPENDENCY_BLOCKED": "debug",
    
    # Transient: One-off network notifications
    "WORKER_HEARTBEAT": "transient"
}

# Strict Event Schemas
EVENT_SCHEMAS = {
    "PIPELINE_CREATED": {
        "required": {"pipeline_type": str, "name": str},
        "optional": {},
        "validation_rules": [
            lambda p: len(p.get("pipeline_type", "")) > 0 or "pipeline_type cannot be empty",
            lambda p: len(p.get("name", "")) > 0 or "name cannot be empty"
        ],
        "replay_semantics": "Initialize pipeline name, type, status as created, and created_at watermark."
    },
    "PIPELINE_COMPLETED": {
        "required": {},
        "optional": {"duration_seconds": (int, float)},
        "validation_rules": [
            lambda p: p.get("duration_seconds", 0) >= 0 or "duration_seconds cannot be negative" if "duration_seconds" in p else True
        ],
        "replay_semantics": "Set pipeline status to completed and record completed_at watermark."
    },
    "PIPELINE_FAILED": {
        "required": {"error_message": str},
        "optional": {},
        "validation_rules": [
            lambda p: len(p.get("error_message", "")) > 0 or "error_message cannot be empty"
        ],
        "replay_semantics": "Set pipeline status to failed, set pipeline completed_at, and record error_message."
    },
    "TASK_CREATED": {
        "required": {"task_type": str, "priority": str},
        "optional": {},
        "validation_rules": [
            lambda p: len(p.get("task_type", "")) > 0 or "task_type cannot be empty",
            lambda p: p.get("priority") in ("low", "medium", "high") or "priority must be one of low, medium, or high"
        ],
        "replay_semantics": "Instantiate pending task with designated priority and empty runtime metrics."
    },
    "TASK_QUEUED": {
        "required": {"queue_name": str},
        "optional": {},
        "validation_rules": [
            lambda p: len(p.get("queue_name", "")) > 0 or "queue_name cannot be empty"
        ],
        "replay_semantics": "Transition task status to pending, record queue timestamp to calculate wait duration."
    },
    "TASK_CLAIMED": {
        "required": {"worker_id": str, "lease_token": str, "lease_duration": (int, float)},
        "optional": {},
        "validation_rules": [
            lambda p: len(p.get("worker_id", "")) > 0 or "worker_id cannot be empty",
            lambda p: len(p.get("lease_token", "")) > 0 or "lease_token cannot be empty",
            lambda p: p.get("lease_duration", 0) > 0 or "lease_duration must be positive"
        ],
        "replay_semantics": "Transition task status to running, assign worker_id/lease_token, calculate lease expiry timestamp, record started_at, set pipeline status to running, and compute queue_wait_duration."
    },
    "LEASE_RENEWED": {
        "required": {"worker_id": str, "lease_token": str, "lease_duration": (int, float)},
        "optional": {},
        "validation_rules": [
            lambda p: len(p.get("worker_id", "")) > 0 or "worker_id cannot be empty",
            lambda p: len(p.get("lease_token", "")) > 0 or "lease_token cannot be empty",
            lambda p: p.get("lease_duration", 0) > 0 or "lease_duration must be positive"
        ],
        "replay_semantics": "Increment lease renewal count, and update lease expiry timestamp."
    },
    "LEASE_EXPIRED": {
        "required": {"worker_id": str, "lease_token": str},
        "optional": {"reason": str},
        "validation_rules": [
            lambda p: len(p.get("worker_id", "")) > 0 or "worker_id cannot be empty",
            lambda p: len(p.get("lease_token", "")) > 0 or "lease_token cannot be empty"
        ],
        "replay_semantics": "Release task back to pending state, reset worker assignment and lease token."
    },
    "TASK_STARTED": {
        "required": {"worker_id": str, "lease_token": str},
        "optional": {},
        "validation_rules": [
            lambda p: len(p.get("worker_id", "")) > 0 or "worker_id cannot be empty",
            lambda p: len(p.get("lease_token", "")) > 0 or "lease_token cannot be empty"
        ],
        "replay_semantics": "Transition task status to running, assign worker_id/lease_token, record started_at, and compute queue_wait_duration."
    },
    "TASK_COMPLETED": {
        "required": {"worker_id": str, "lease_token": str},
        "optional": {"output_artifact_ids": list},
        "validation_rules": [
            lambda p: len(p.get("worker_id", "")) > 0 or "worker_id cannot be empty",
            lambda p: len(p.get("lease_token", "")) > 0 or "lease_token cannot be empty"
        ],
        "replay_semantics": "Transition task status to completed, record completed_at and output artifact IDs, and compute task execution duration."
    },
    "TASK_FAILED": {
        "required": {"worker_id": str, "lease_token": str, "error_message": str},
        "optional": {},
        "validation_rules": [
            lambda p: len(p.get("worker_id", "")) > 0 or "worker_id cannot be empty",
            lambda p: len(p.get("lease_token", "")) > 0 or "lease_token cannot be empty",
            lambda p: len(p.get("error_message", "")) > 0 or "error_message cannot be empty"
        ],
        "replay_semantics": "Transition task status to failed, increment retry_count, and record error_message."
    },
    "TASK_RECOVERED": {
        "required": {"recovered_count": int},
        "optional": {"reason": str},
        "validation_rules": [
            lambda p: p.get("recovered_count", 0) >= 0 or "recovered_count cannot be negative"
        ],
        "replay_semantics": "Mark task pending, clear worker lease, increment recovered count, transition pipeline status to recovering if currently running."
    },
    "TASK_BLOCKED": {
        "required": {"blocked_reason": str},
        "optional": {},
        "validation_rules": [
            lambda p: len(p.get("blocked_reason", "")) > 0 or "blocked_reason cannot be empty"
        ],
        "replay_semantics": "Set task status to blocked and record blocked_reason."
    },
    "TASK_RELEASED": {
        "required": {"priority": str},
        "optional": {},
        "validation_rules": [
            lambda p: p.get("priority") in ("low", "medium", "high") or "priority must be one of low, medium, or high"
        ],
        "replay_semantics": "Reset blocked task status back to pending and remove blocked_reason."
    },
    "BACKPRESSURE_DEFERRED": {
        "required": {"priority": str, "deferred_at": str},
        "optional": {},
        "validation_rules": [
            lambda p: p.get("priority") in ("low", "medium", "high") or "priority must be one of low, medium, or high",
            lambda p: len(p.get("deferred_at", "")) > 0 or "deferred_at cannot be empty"
        ],
        "replay_semantics": "Set task status to deferred and record deferred_at timestamp."
    },
    "PRIORITY_ESCALATED": {
        "required": {"old_priority": str, "new_priority": str},
        "optional": {},
        "validation_rules": [
            lambda p: p.get("old_priority") in ("low", "medium", "high") or "old_priority must be one of low, medium, or high",
            lambda p: p.get("new_priority") in ("low", "medium", "high") or "new_priority must be one of low, medium, or high"
        ],
        "replay_semantics": "Update task priority to new_priority."
    },
    "ARTIFACT_CREATED": {
        "required": {"artifact_id": int, "artifact_type": str, "storage_uri": str},
        "optional": {},
        "validation_rules": [
            lambda p: p.get("artifact_id", 0) > 0 or "artifact_id must be a positive integer",
            lambda p: len(p.get("artifact_type", "")) > 0 or "artifact_type cannot be empty",
            lambda p: len(p.get("storage_uri", "")) > 0 or "storage_uri cannot be empty"
        ],
        "replay_semantics": "Reconstruct artifact lineage records and link to task output lists."
    },
    "DEPENDENCY_RELEASED": {
        "required": {"parent_task_id": int, "child_task_id": int},
        "optional": {},
        "validation_rules": [
            lambda p: p.get("parent_task_id", 0) > 0 or "parent_task_id must be positive",
            lambda p: p.get("child_task_id", 0) > 0 or "child_task_id must be positive"
        ],
        "replay_semantics": "Record child dependency release for parent_task_id as satisfied (True) and reset child status to pending."
    },
    "DEPENDENCY_BLOCKED": {
        "required": {"parent_task_id": int, "child_task_id": int},
        "optional": {},
        "validation_rules": [
            lambda p: p.get("parent_task_id", 0) > 0 or "parent_task_id must be positive",
            lambda p: p.get("child_task_id", 0) > 0 or "child_task_id must be positive"
        ],
        "replay_semantics": "Record child dependency release for parent_task_id as blocked (False) and transition child status to blocked."
    },
    "STALE_WORKER_UPDATE_REJECTED": {
        "required": {"worker_id": str, "lease_token": str},
        "optional": {"reason": str},
        "validation_rules": [
            lambda p: len(p.get("worker_id", "")) > 0 or "worker_id cannot be empty",
            lambda p: len(p.get("lease_token", "")) > 0 or "lease_token cannot be empty"
        ],
        "replay_semantics": "No replay state change; recorded for worker audit purposes."
    },
    "PIPELINE_OWNERSHIP_TAKEN_OVER": {
        "required": {"instance_id": str, "ownership_version": int},
        "optional": {},
        "validation_rules": [
            lambda p: len(p.get("instance_id", "")) > 0 or "instance_id cannot be empty",
            lambda p: p.get("ownership_version", 0) >= 0 or "ownership_version must be non-negative"
        ],
        "replay_semantics": "Change pipeline orchestrator owner instance and increment fencing token version."
    },
    "TASK_TRACE": {
        "required": {},
        "optional": {"message": str, "worker_id": str, "step": str},
        "validation_rules": [],
        "replay_semantics": "Telemetry-only trace log; no state replay needed."
    },
    "WORKER_HEARTBEAT": {
        "required": {},
        "optional": {"worker_id": str, "status": str},
        "validation_rules": [],
        "replay_semantics": "Telemetry-only; no state replay needed."
    }
}

# Telemetry event categories that pass validation without full schema checks
EVENT_CATEGORIES = {"TASK_TRACE", "WORKER_HEARTBEAT"}

# Event versioning constants
CURRENT_EVENT_VERSION = 1
CURRENT_SCHEMA_VERSION = "2.0"

def validate_event_payload(event_type, payload):
    """
    Validates that the given payload meets the schema requirements for event_type.
    Raises ValueError on validation failure.
    """
    event_type = event_type.upper()
    if event_type not in EVENT_SCHEMAS:
        # If event type doesn't have a schema, check if it's transient/telemetry and allow empty schema
        if event_type in EVENT_CATEGORIES:
            return
        raise ValueError(f"Unknown event type: {event_type}")
        
    schema = EVENT_SCHEMAS[event_type]
    req = schema["required"]
    opt = schema["optional"]
    
    # Check required fields
    for field, expected_type in req.items():
        if field not in payload:
            raise ValueError(f"Event {event_type} payload missing required field: {field}")
        val = payload[field]
        if not isinstance(val, expected_type):
            raise ValueError(f"Event {event_type} field '{field}' expects type {expected_type}, got {type(val)}")
            
    # Check optional fields
    for field, expected_type in opt.items():
        if field in payload:
            val = payload[field]
            if not isinstance(val, expected_type):
                raise ValueError(f"Event {event_type} optional field '{field}' expects type {expected_type}, got {type(val)}")

    # Check validation rules
    if "validation_rules" in schema:
        for rule in schema["validation_rules"]:
            res = rule(payload)
            if isinstance(res, str):
                raise ValueError(f"Event {event_type} payload validation failed: {res}")
            elif not res:
                raise ValueError(f"Event {event_type} payload validation failed")

def publish_event(db, event_type, pipeline_id=None, task_id=None, message=None, worker_id=None, lease_token=None, correlation_id=None, payload=None, segment_index=0):
    """
    Validates, categorizes, and logs an orchestration event into the database.
    """
    event_type = event_type.upper()
    payload = payload or {}
    
    if pipeline_id and segment_index == 0:
        latest_evt = db.query(OrchestrationEvent).filter(
            OrchestrationEvent.pipeline_id == pipeline_id
        ).order_by(OrchestrationEvent.id.desc()).first()
        if latest_evt:
            segment_index = latest_evt.segment_index or 0
    
    # Fallback mappings for old event names
    mapping = {
        "TASK_TIMED_OUT": "LEASE_EXPIRED",
        "TASK_RETRIED": "TASK_QUEUED",
        "TASK_REQUEUED": "TASK_QUEUED",
        "TASK_CANCELLED": "TASK_FAILED",
        "DEPENDENCY_WAITING": "DEPENDENCY_BLOCKED",
        "DEPENDENCY_RESOLVED": "DEPENDENCY_RELEASED",
        "TASK_LEASE_RENEWAL_REJECTED": "TASK_FAILED",
        "TASK_LEASE_RENEWED": "LEASE_RENEWED",
        "TASK_RECOVERED_AFTER_LEASE_EXPIRY": "TASK_RECOVERED",
        "MAX_RETRIES_EXCEEDED_AFTER_LEASE_EXPIRY": "TASK_FAILED",
        "INPUT_ARTIFACT_RECEIVED": "ARTIFACT_CREATED"
    }
    
    event_type = mapping.get(event_type, event_type)
    
    # 1. Validate payload
    validate_event_payload(event_type, payload)
    
    # 2. Categorize
    category = EVENT_CATEGORIES.get(event_type, "operational")
    
    # 3. Write to DB
    evt = OrchestrationEvent(
        pipeline_id=pipeline_id,
        task_id=task_id,
        event_type=event_type,
        event_category=category,
        message=message,
        worker_id=worker_id,
        lease_token=lease_token,
        correlation_id=correlation_id,
        payload_json=json.dumps(payload),
        segment_index=segment_index,
        event_version=CURRENT_EVENT_VERSION,
        schema_version=CURRENT_SCHEMA_VERSION
    )
    db.add(evt)
    db.flush() # populate ID
    
    # Automatically trigger periodic snapshot generation for critical paths (avoid race condition)
    if pipeline_id and category == "critical" and evt.id % 10 == 0:
        try:
            create_pipeline_snapshot(db, pipeline_id)
        except Exception as e:
            logger.warning(f"Failed to generate auto-snapshot for pipeline {pipeline_id}: {e}")
            
    return evt

def create_pipeline_snapshot(db, pipeline_id):
    """
    Creates a snapshot of the pipeline state up to the current last event.
    """
    # 1. Get the last event ID
    last_event = db.query(OrchestrationEvent).filter(
        OrchestrationEvent.pipeline_id == pipeline_id
    ).order_by(OrchestrationEvent.id.desc()).first()
    
    if not last_event:
        return None
        
    last_event_id = last_event.id
    
    # 2. Reconstruct state up to last_event_id (isolated replay)
    state = reconstruct_pipeline_state(db, pipeline_id, target_event_id=last_event_id, skip_snapshot=True)
    
    # Remove critical path from snapshot data as it is a derived metric calculated at runtime
    if "critical_path" in state:
        state.pop("critical_path")
        
    # Compress snapshot data
    snapshot_data = gzip.compress(json.dumps(state).encode())
    
    # 3. Create snapshot
    snapshot = OrchestrationSnapshot(
        pipeline_id=pipeline_id,
        last_event_id=last_event_id,
        snapshot_data=snapshot_data
    )
    db.add(snapshot)
    db.commit()
    return snapshot

def create_segmented_snapshot(db, pipeline_id, segment_index):
    """
    Creates a snapshot of the pipeline state up to the end of the given segment_index.
    """
    last_event = db.query(OrchestrationEvent).filter(
        OrchestrationEvent.pipeline_id == pipeline_id,
        OrchestrationEvent.segment_index == segment_index
    ).order_by(OrchestrationEvent.id.desc()).first()
    
    if not last_event:
        return None
        
    last_event_id = last_event.id
    state = reconstruct_pipeline_state(db, pipeline_id, target_event_id=last_event_id, skip_snapshot=True)
    
    if "critical_path" in state:
        state.pop("critical_path")
        
    snapshot_data = gzip.compress(json.dumps(state).encode())
    
    existing = db.query(OrchestrationSnapshot).filter(
        OrchestrationSnapshot.pipeline_id == pipeline_id,
        OrchestrationSnapshot.segment_index == segment_index
    ).first()
    
    if existing:
        existing.last_event_id = last_event_id
        existing.snapshot_data = snapshot_data
        snapshot = existing
    else:
        snapshot = OrchestrationSnapshot(
            pipeline_id=pipeline_id,
            last_event_id=last_event_id,
            snapshot_data=snapshot_data,
            segment_index=segment_index
        )
        db.add(snapshot)
    
    db.commit()
    return snapshot

def advance_pipeline_segment(db, pipeline_id):
    """
    Increments the current segment index of a pipeline by creating a snapshot of the current state,
    and returns the new segment index.
    """
    current_segment = 0
    latest_evt = db.query(OrchestrationEvent).filter(
        OrchestrationEvent.pipeline_id == pipeline_id
    ).order_by(OrchestrationEvent.id.desc()).first()
    if latest_evt:
        current_segment = latest_evt.segment_index or 0
        
    next_segment = current_segment + 1
    
    create_segmented_snapshot(db, pipeline_id, current_segment)
    
    publish_event(
        db=db,
        event_type="PIPELINE_OWNERSHIP_TAKEN_OVER",
        pipeline_id=pipeline_id,
        message=f"Advanced pipeline segment to {next_segment}",
        payload={"instance_id": "system", "ownership_version": next_segment},
        segment_index=next_segment
    )
    
    return next_segment

def compact_completed_pipeline_segments(db):
    """
    Finds completed segments of pipelines and compacts them by ensuring they have snapshots
    and deleting raw telemetry/debug events.
    """
    pipelines = db.query(Pipeline).all()
    for pipe in pipelines:
        latest_evt = db.query(OrchestrationEvent).filter(
            OrchestrationEvent.pipeline_id == pipe.id
        ).order_by(OrchestrationEvent.id.desc()).first()
        if not latest_evt:
            continue
        max_segment = latest_evt.segment_index or 0
        
        is_finished = pipe.status in ('completed', 'failed', 'blocked', 'cancelled')
        completed_segments = list(range(max_segment + 1)) if is_finished else list(range(max_segment))
        
        for S in completed_segments:
            snapshot = db.query(OrchestrationSnapshot).filter(
                OrchestrationSnapshot.pipeline_id == pipe.id,
                OrchestrationSnapshot.segment_index == S
            ).first()
            
            if not snapshot:
                snapshot = create_segmented_snapshot(db, pipe.id, S)
                
            if snapshot:
                stmt = text(
                    "DELETE FROM orchestration_events "
                    "WHERE pipeline_id = :pid AND segment_index = :S "
                    "AND event_category IN ('telemetry', 'debug', 'transient')"
                )
                db.execute(stmt, {"pid": pipe.id, "S": S})
                db.commit()

def reconstruct_pipeline_state(db, pipeline_id, target_event_id=None, target_time=None, skip_snapshot=False):
    """
    Deterministically reconstructs the state of a pipeline at target_event_id or target_time.
    Uses the closest available snapshot before the target threshold to skip full history replays.
    Replay is sandboxed, read-only, and has zero side-effects.
    """
    # Initial empty state structure
    state = {
        "pipeline": {
            "id": pipeline_id,
            "name": "",
            "pipeline_type": "",
            "status": "created",
            "created_at": None,
            "started_at": None,
            "completed_at": None,
            "error_message": None,
            "owner_instance_id": None,
            "ownership_version": 0
        },
        "tasks": {},
        "artifacts": [],
        "dependencies": {}, # task_id -> list of depends_on_ids
        "dependency_releases": {} # child_task_id -> {parent_task_id: bool}
    }
    
    start_event_id = 0
    snapshot_segment = -1  # segment index of the snapshot we base on
    
    # 1. Determine target segment
    if target_event_id is not None:
        target_evt = db.query(OrchestrationEvent).filter(OrchestrationEvent.id == target_event_id).first()
        if target_evt:
            target_segment = target_evt.segment_index or 0
    else:
        latest_evt = db.query(OrchestrationEvent).filter(
            OrchestrationEvent.pipeline_id == pipeline_id
        ).order_by(OrchestrationEvent.id.desc()).first()
        target_segment = latest_evt.segment_index if latest_evt else 0

    # 2. Query nearest snapshot if not skipped
    if not skip_snapshot:
        snapshot_query = db.query(OrchestrationSnapshot).filter(OrchestrationSnapshot.pipeline_id == pipeline_id)
        if target_event_id is not None:
            snapshot_query = snapshot_query.filter(OrchestrationSnapshot.last_event_id <= target_event_id)
        
        snapshot = snapshot_query.filter(OrchestrationSnapshot.segment_index <= target_segment)\
                                 .order_by(OrchestrationSnapshot.segment_index.desc(), OrchestrationSnapshot.last_event_id.desc())\
                                 .first()
        
        if snapshot:
            # Load state from snapshot (decompress if needed)
            snapshot_data = snapshot.snapshot_data
            # Defensive: encode to bytes if DB driver returned a str (causes
            # "string argument without an encoding" inside gzip.decompress)
            if isinstance(snapshot_data, str):
                snapshot_data = snapshot_data.encode('utf-8')
            if isinstance(snapshot_data, bytes):
                try:
                    snapshot_data = gzip.decompress(snapshot_data)
                except gzip.BadGzipFile:
                    # Already uncompressed or legacy plain JSON bytes
                    pass
            if isinstance(snapshot_data, bytes):
                snapshot_data = snapshot_data.decode('utf-8')
            state = json.loads(snapshot_data)
            start_event_id = snapshot.last_event_id
            snapshot_segment = snapshot.segment_index or 0
            
    # 3. Retrieve events after the snapshot (or all if no snapshot)
    # We need all events that happened after the snapshot's last_event_id,
    # but still within the target segment boundaries, including events from
    # later segments up to target_segment.
    # Condition: (segment == snapshot_segment AND id > start_event_id) OR (segment > snapshot_segment AND segment <= target_segment)
    event_query = db.query(OrchestrationEvent).filter(
        OrchestrationEvent.pipeline_id == pipeline_id
    )
    if start_event_id > 0:
        event_query = event_query.filter(
            or_(
                and_(
                    OrchestrationEvent.segment_index == snapshot_segment,
                    OrchestrationEvent.id > start_event_id
                ),
                and_(
                    OrchestrationEvent.segment_index > snapshot_segment,
                    OrchestrationEvent.segment_index <= target_segment
                )
            )
        )
    else:
        event_query = event_query.filter(OrchestrationEvent.segment_index <= target_segment)
    
    if target_event_id is not None:
        event_query = event_query.filter(OrchestrationEvent.id <= target_event_id)
    if target_time is not None:
        if isinstance(target_time, str):
            try:
                target_time = datetime.fromisoformat(target_time)
            except Exception:
                pass
        if isinstance(target_time, datetime):
            event_query = event_query.filter(OrchestrationEvent.created_at <= target_time)
            
    events = event_query.order_by(OrchestrationEvent.id.asc()).all()
    
    # Keep track of task queue events to compute queue wait time during replay
    task_queued_times = {}
    
    # Apply events sequentially to state (Deterministic Replay)
    for evt in events:
        event_type = evt.event_type.upper()
        payload = json.loads(evt.payload_json) if evt.payload_json else {}
        tid = str(evt.task_id) if evt.task_id else None
        
        evt_created_str = evt.created_at.isoformat() if evt.created_at else None
        
        if event_type == "PIPELINE_CREATED":
            state["pipeline"]["name"] = payload.get("name", "")
            state["pipeline"]["pipeline_type"] = payload.get("pipeline_type", "")
            state["pipeline"]["status"] = "created"
            state["pipeline"]["created_at"] = evt_created_str
            
        elif event_type == "PIPELINE_COMPLETED":
            state["pipeline"]["status"] = "completed"
            state["pipeline"]["completed_at"] = evt_created_str
            
        elif event_type == "PIPELINE_FAILED":
            state["pipeline"]["status"] = "failed"
            state["pipeline"]["completed_at"] = evt_created_str
            state["pipeline"]["error_message"] = payload.get("error_message")
            
        elif event_type == "PIPELINE_OWNERSHIP_TAKEN_OVER":
            state["pipeline"]["owner_instance_id"] = payload.get("instance_id")
            state["pipeline"]["ownership_version"] = payload.get("ownership_version")
            
        elif event_type == "TASK_CREATED":
            if tid:
                state["tasks"][tid] = {
                    "id": evt.task_id,
                    "type": payload.get("task_type", ""),
                    "status": "pending",
                    "priority": payload.get("priority", "medium"),
                    "retry_count": 0,
                    "max_retries": 3,
                    "error_message": None,
                    "created_at": evt_created_str,
                    "started_at": None,
                    "completed_at": None,
                    "assigned_worker_id": None,
                    "lease_token": None,
                    "lease_expires_at": None,
                    "recovered_count": 0,
                    "lease_renewal_count": 0,
                    "input_artifact_ids": [],
                    "output_artifact_ids": [],
                    "blocked_reason": None,
                    "deferred_at": None,
                    "queue_wait_duration": 0.0,
                    "execution_duration": 0.0
                }
                # Initialize dependencies
                state["dependencies"][tid] = payload.get("dependencies", [])
                
        elif event_type == "TASK_QUEUED":
            if tid and tid in state["tasks"]:
                state["tasks"][tid]["status"] = "pending"
                task_queued_times[tid] = evt.created_at
                
        elif event_type == "TASK_CLAIMED":
            if tid and tid in state["tasks"]:
                t_state = state["tasks"][tid]
                t_state["status"] = "running"
                t_state["started_at"] = evt_created_str
                # Use payload or fallback to event columns
                t_state["assigned_worker_id"] = payload.get("worker_id") or evt.worker_id
                t_state["lease_token"] = payload.get("lease_token") or evt.lease_token
                duration = payload.get("lease_duration", 30)
                if evt.created_at:
                    t_state["lease_expires_at"] = (evt.created_at + timedelta(seconds=duration)).isoformat()
                if not state["pipeline"]["started_at"]:
                    state["pipeline"]["started_at"] = evt_created_str
                    state["pipeline"]["status"] = "running"
                if tid in task_queued_times and evt.created_at:
                    t_state["queue_wait_duration"] = round(
                        (evt.created_at - task_queued_times[tid]).total_seconds(), 2
                    )
                
        elif event_type == "LEASE_RENEWED":
            if tid and tid in state["tasks"]:
                t_state = state["tasks"][tid]
                t_state["lease_renewal_count"] += 1
                duration = payload.get("lease_duration", 30)
                if evt.created_at:
                    t_state["lease_expires_at"] = (evt.created_at + timedelta(seconds=duration)).isoformat()
                    
        elif event_type == "LEASE_EXPIRED":
            if tid and tid in state["tasks"]:
                t_state = state["tasks"][tid]
                t_state["status"] = "pending"
                t_state["lease_token"] = None
                t_state["assigned_worker_id"] = None
                
        elif event_type == "TASK_STARTED":
            if tid and tid in state["tasks"]:
                t_state = state["tasks"][tid]
                t_state["status"] = "running"
                t_state["started_at"] = evt_created_str
                t_state["assigned_worker_id"] = payload.get("worker_id") or evt.worker_id
                t_state["lease_token"] = payload.get("lease_token") or evt.lease_token
                if not state["pipeline"]["started_at"]:
                    state["pipeline"]["started_at"] = evt_created_str
                    state["pipeline"]["status"] = "running"
                if tid in task_queued_times and evt.created_at:
                    t_state["queue_wait_duration"] = round(
                        (evt.created_at - task_queued_times[tid]).total_seconds(), 2
                    )
                    
        elif event_type == "TASK_COMPLETED":
            if tid and tid in state["tasks"]:
                t_state = state["tasks"][tid]
                t_state["status"] = "completed"
                t_state["completed_at"] = evt_created_str
                if t_state["started_at"] and evt.created_at:
                    st_dt = datetime.fromisoformat(t_state["started_at"])
                    t_state["execution_duration"] = round(
                        (evt.created_at - st_dt).total_seconds(), 2
                    )
                t_state["output_artifact_ids"] = payload.get("output_artifact_ids", [])
                
        elif event_type == "TASK_FAILED":
            if tid and tid in state["tasks"]:
                t_state = state["tasks"][tid]
                t_state["status"] = "failed"
                t_state["error_message"] = payload.get("error_message")
                t_state["retry_count"] += 1
                
        elif event_type == "TASK_RECOVERED":
            if tid and tid in state["tasks"]:
                t_state = state["tasks"][tid]
                t_state["status"] = "pending"
                t_state["recovered_count"] = payload.get("recovered_count", t_state["recovered_count"] + 1)
                t_state["lease_token"] = None
                t_state["assigned_worker_id"] = None
                if state["pipeline"]["status"] == "running":
                    state["pipeline"]["status"] = "recovering"
                
        elif event_type in ("TASK_BLOCKED", "DEPENDENCY_BLOCKED"):
            if tid and tid in state["tasks"]:
                state["tasks"][tid]["status"] = "blocked"
                state["tasks"][tid]["blocked_reason"] = payload.get("blocked_reason")
                
        elif event_type in ("TASK_RELEASED", "DEPENDENCY_RELEASED"):
            if tid and tid in state["tasks"]:
                state["tasks"][tid]["status"] = "pending"
                state["tasks"][tid]["blocked_reason"] = None
                
        elif event_type == "BACKPRESSURE_DEFERRED":
            if tid and tid in state["tasks"]:
                state["tasks"][tid]["status"] = "deferred"
                state["tasks"][tid]["deferred_at"] = evt_created_str
                
        elif event_type == "PRIORITY_ESCALATED":
            if tid and tid in state["tasks"]:
                state["tasks"][tid]["priority"] = payload.get("new_priority", "medium")
                
        elif event_type == "ARTIFACT_CREATED":
            art = {
                "id": payload.get("artifact_id"),
                "pipeline_id": pipeline_id,
                "task_id": evt.task_id,
                "artifact_type": payload.get("artifact_type"),
                "storage_uri": payload.get("storage_uri"),
                "created_at": evt_created_str
            }
            state["artifacts"].append(art)
            if tid and tid in state["tasks"]:
                art_id = payload.get("artifact_id")
                if art_id not in state["tasks"][tid]["output_artifact_ids"]:
                    state["tasks"][tid]["output_artifact_ids"].append(art_id)
                    
        elif event_type == "DEPENDENCY_RELEASED":
            parent = str(payload.get("parent_task_id"))
            child = str(payload.get("child_task_id"))
            if child not in state["dependency_releases"]:
                state["dependency_releases"][child] = {}
            state["dependency_releases"][child][parent] = True
            
        elif event_type == "DEPENDENCY_BLOCKED":
            parent = str(payload.get("parent_task_id"))
            child = str(payload.get("child_task_id"))
            if child not in state["dependency_releases"]:
                state["dependency_releases"][child] = {}
            state["dependency_releases"][child][parent] = False

    # Compute derived metrics (Critical Path)
    state["critical_path"] = compute_critical_path(state)
    return state

def compute_critical_path(state):
    """
    Computes the critical path of the reconstructed pipeline DAG.
    Critical path is defined as the sequence of dependent tasks that takes the longest total duration
    (queue_wait_duration + execution_duration).
    """
    tasks = state.get("tasks", {})
    if not tasks:
        return []
        
    # Build adjacency list: node -> list of children
    adj = {tid: [] for tid in tasks}
    in_degree = {tid: 0 for tid in tasks}
    
    deps = state.get("dependencies", {})
    
    for child, parents in deps.items():
        child_str = str(child)
        for parent in parents:
            parent_str = str(parent)
            if parent_str in adj:
                adj[parent_str].append(child_str)
                in_degree[child_str] += 1
                
    weights = {}
    for tid, tdata in tasks.items():
        w = tdata.get("queue_wait_duration", 0.0) + tdata.get("execution_duration", 0.0)
        weights[tid] = w if w is not None else 0.0

    # Topological sort using deque for O(V+E)
    topo_order = []
    zero_in = deque([tid for tid in tasks if in_degree[tid] == 0])
    in_deg_temp = dict(in_degree)
    
    while zero_in:
        curr = zero_in.popleft()
        topo_order.append(curr)
        for child in adj[curr]:
            in_deg_temp[child] -= 1
            if in_deg_temp[child] == 0:
                zero_in.append(child)
                
    if len(topo_order) != len(tasks):
        # Fallback in case of cycle (should not happen)
        topo_order = list(tasks.keys())
        
    dist = {}
    for tid in tasks:
        dist[tid] = (weights[tid], [int(tid)])
        
    for node in topo_order:
        curr_dist, curr_path = dist[node]
        for child in adj[node]:
            child_weight = weights[child]
            new_dist = curr_dist + child_weight
            if child not in dist or new_dist > dist[child][0]:
                dist[child] = (new_dist, curr_path + [int(child)])
                
    max_tid = None
    max_val = -1.0
    for tid, (val, path) in dist.items():
        if val > max_val:
            max_val = val
            max_tid = tid
            
    if max_tid is not None:
        return dist[max_tid][1]
    return []

def purge_transient_events(db, days_retention=7):
    """
    Cleans up old telemetry and transient events to prevent unbounded growth of logs.
    """
    cutoff = datetime.now() - timedelta(days=days_retention)
    stmt = text(
        "DELETE FROM orchestration_events "
        "WHERE event_category IN ('telemetry', 'debug', 'transient') "
        "AND created_at < :cutoff"
    )
    db.execute(stmt, {"cutoff": cutoff})
    db.commit()