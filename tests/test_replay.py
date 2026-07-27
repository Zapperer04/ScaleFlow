import json
import pytest
from backend.models import SessionLocal, Pipeline, Task, OrchestrationEvent, TaskLog, PipelineStatus, TaskStatus, EventCategory
from backend.replay import build_replay, analyze_execution

def test_replay_read_only_and_rca():
    db = SessionLocal()
    try:
        # 1. Create a dummy pipeline
        pipeline = Pipeline(
            name="test_replay_pipeline",
            pipeline_type="MR-RAG",
            status=PipelineStatus.failed
        )
        db.add(pipeline)
        db.commit()
        db.refresh(pipeline)

        # 2. Create tasks
        t1 = Task(
            type="preprocess_document",
            data=json.dumps({"correlation_id": "corr-123"}),
            status=TaskStatus.completed,
            pipeline_id=pipeline.id
        )
        t2 = Task(
            type="parse_document",
            data=json.dumps({"correlation_id": "corr-123"}),
            status=TaskStatus.failed,
            pipeline_id=pipeline.id,
            error_message="VLM processing failed"
        )
        db.add(t1)
        db.add(t2)
        db.commit()
        db.refresh(t1)
        db.refresh(t2)

        # 3. Create events
        ev1 = OrchestrationEvent(
            pipeline_id=pipeline.id,
            task_id=t1.id,
            event_type="task_completed",
            event_category=EventCategory.operational,
            message="Task completed successfully",
            correlation_id="corr-123",
            payload_json="{}"
        )
        ev2 = OrchestrationEvent(
            pipeline_id=pipeline.id,
            task_id=t2.id,
            event_type="task_failed",
            event_category=EventCategory.operational,
            message="VLM processing failed",
            correlation_id="corr-123",
            payload_json="{}"
        )
        db.add(ev1)
        db.add(ev2)
        db.commit()

        # Test build_replay
        replay = build_replay(db, pipeline.id)
        assert replay is not None
        assert replay["pipeline_id"] == pipeline.id
        assert replay["correlation_id"] == "corr-123"
        assert len(replay["events"]) >= 2
        assert replay["version"] == 1

        # Check metadata
        assert "metadata" in replay
        meta = replay["metadata"]
        assert meta["event_count"] == len(replay["events"])
        assert meta["snapshot_count"] == len(replay["events"])
        assert meta["task_count"] == 2
        assert meta["worker_count"] == 0 # no worker IDs assigned in this dummy test
        assert meta["first_timestamp"] == replay["events"][0]["timestamp"]
        assert meta["last_timestamp"] == replay["events"][-1]["timestamp"]


        # Check fields of normalized events
        for e in replay["events"]:
            assert "timestamp" in e
            assert "source" in e
            assert "event_type" in e
            assert "pipeline_id" in e
            assert "task_id" in e
            assert "correlation_id" in e

        analysis = analyze_execution(replay)
        assert analysis["root_cause"] != ""
        assert analysis["confidence"] == "high"
        assert analysis["rule"] == "explicit_failure"
        assert analysis["failed_task"]["task_id"] == t2.id
        assert len(analysis["critical_path"]) > 0

        # Clean up database
        db.delete(ev2)
        db.delete(ev1)
        db.delete(t2)
        db.delete(t1)
        db.delete(pipeline)
        db.commit()
    finally:
        db.close()
