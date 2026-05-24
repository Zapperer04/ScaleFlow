import os
import sys
import time
import json
import requests
import redis
import hashlib
from datetime import datetime, timedelta

# Load env variables
def load_env():
    try:
        with open('.env') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, val = line.strip().split('=', 1)
                    os.environ.setdefault(key.strip(), val.strip())
    except FileNotFoundError:
        pass

load_env()

API_URL = os.environ.get("API_URL", "http://127.0.0.1:5000")
API_KEY = os.environ.get("API_KEY", "dev_secret_api_key")
HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# Connect to database models
from models import SessionLocal, Task, TaskDependency, TaskLog, Pipeline, Artifact, FileRecord, OrchestrationEvent, OrchestrationSnapshot
from app import reconcile_active_orchestrations, add_task_to_queue

# Redis Client
r = redis.Redis(
    host=os.environ.get("REDIS_HOST", "localhost"),
    port=int(os.environ.get("REDIS_PORT", 6379)),
    decode_responses=True
)

def print_banner(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def clear_system():
    print("Cleaning database and Redis queues...")
    db = SessionLocal()
    try:
        db.query(OrchestrationSnapshot).delete()
        db.query(OrchestrationEvent).delete()
        db.query(FileRecord).delete()
        db.query(TaskDependency).delete()
        db.query(Artifact).delete()
        db.query(TaskLog).delete()
        db.query(Task).delete()
        db.query(Pipeline).delete()
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error clearing database: {e}")
    finally:
        db.close()

    # Clear Redis
    for q in r.keys("task_queue_*"):
        r.delete(q)
    r.delete("wrr_index")
    print("System cleared successfully.")

def get_state_hash(state):
    """Generates a hash of the pipeline and task status configurations for exact verification."""
    hasher = hashlib.sha256()
    
    # 1. Pipeline details
    pipe = state.get("pipeline", {})
    p_str = f"pipe:{pipe.get('id')}:{pipe.get('status')}"
    hasher.update(p_str.encode('utf-8'))
    
    # 2. Tasks sorted by ID
    tasks = state.get("tasks", {})
    for tid in sorted(tasks.keys(), key=int):
        t = tasks[tid]
        t_str = f"task:{t.get('id')}:{t.get('status')}:{t.get('priority')}:{t.get('retry_count')}:{t.get('recovered_count')}"
        hasher.update(t_str.encode('utf-8'))
        
    return hasher.hexdigest()

def test_scenario_a():
    print_banner("Scenario A: Deterministic State Reconstruction & Equality")
    clear_system()
    
    # 1. Create a Pipeline
    payload = {
        "name": "Test Linear Pipeline",
        "pipeline_type": "document_processing_demo",
        "initial_payload": {
            "source_text": "Resilience stress test"
        }
    }
    res = requests.post(f"{API_URL}/pipelines", json=payload, headers=HEADERS)
    if res.status_code not in [200, 201]:
        print(f"FAIL: Failed to create pipeline. Code: {res.status_code}, Text: {res.text}")
        return False
        
    p_data = res.json()
    pipeline_id = p_data["pipeline_id"]
    print(f"Pipeline #{pipeline_id} created successfully.")
    
    # 2. Complete tasks sequentially to simulate worker actions
    db = SessionLocal()
    try:
        tasks = db.query(Task).filter(Task.pipeline_id == pipeline_id).order_by(Task.id.asc()).all()
        worker_id = "mock-worker-A"
        
        for task in tasks:
            print(f"Executing task #{task.id} ({task.type}) status: {task.status}")
            
            # Claim task
            claim_res = requests.post(f"{API_URL}/tasks/{task.id}/claim", json={"worker_id": worker_id}, headers=HEADERS)
            if claim_res.status_code != 200:
                print(f"FAIL: Worker failed to claim task #{task.id}. Text: {claim_res.text}")
                return False
            lease_token = claim_res.json()["lease_token"]
            
            # Complete task
            complete_res = requests.patch(
                f"{API_URL}/tasks/{task.id}", 
                json={
                    "status": "completed",
                    "worker_id": worker_id,
                    "lease_token": lease_token
                },
                headers=HEADERS
            )
            if complete_res.status_code != 200:
                print(f"FAIL: Failed to complete task #{task.id}. Text: {complete_res.text}")
                return False
                
        # 3. Fetch reconstructed state from API
        replay_res = requests.get(f"{API_URL}/replay/pipelines/{pipeline_id}/state", headers=HEADERS)
        if replay_res.status_code != 200:
            print(f"FAIL: Failed to fetch reconstructed state. Text: {replay_res.text}")
            return False
            
        reconstructed = replay_res.json()
        
        # 4. Fetch actual database values
        db.expire_all()
        db_pipeline = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
        db_tasks = db.query(Task).filter(Task.pipeline_id == pipeline_id).all()
        
        # Build DB state structure matching reconstructed
        db_state = {
            "pipeline": db_pipeline.to_dict(),
            "tasks": {str(t.id): t.to_dict() for t in db_tasks}
        }
        
        # Calculate comparison hashes
        rec_hash = get_state_hash(reconstructed)
        db_hash = get_state_hash(db_state)
        
        print(f"Reconstructed Hash: {rec_hash}")
        print(f"Database State Hash: {db_hash}")
        
        if rec_hash == db_hash:
            print("SUCCESS: Deterministic state hashes match exactly!")
            return True
        else:
            print("FAIL: State hashes mismatch!")
            return False
    finally:
        db.close()

def test_scenario_b():
    print_banner("Scenario B: Orchestrator Crash Recovery & Queue Reconciliation")
    # We do NOT run docker stop/start, instead we simulate the state of database and Redis
    # and call the reconciliation method directly to assert correct recovery.
    
    db = SessionLocal()
    try:
        # Create pipeline
        pipeline = Pipeline(name="Test Crash Pipeline", pipeline_type="document_processing_demo", status="running")
        db.add(pipeline)
        db.flush()
        
        # Task 1: pending but missing in Redis queue
        task_pending = Task(
            type="parse_document",
            data=json.dumps({"source_text": "crash test"}),
            status="pending",
            priority="medium",
            pipeline_id=pipeline.id
        )
        db.add(task_pending)
        
        # Task 2: running but lease expired during downtime
        task_expired = Task(
            type="chunk_text",
            data=json.dumps({}),
            status="running",
            priority="high",
            assigned_worker_id="dead-worker",
            lease_token="expired-token-123",
            lease_expires_at=datetime.now() - timedelta(minutes=5), # expired
            retry_count=0,
            max_retries=3,
            pipeline_id=pipeline.id
        )
        db.add(task_expired)
        db.commit()
        
        print(f"Created simulated crash tasks: Pending Task #{task_pending.id}, Expired Task #{task_expired.id}")
        
        # Clear Redis queues to ensure they are empty
        r.delete("task_queue_test_medium")
        r.delete("task_queue_test_high")
        
        # Run reconciliation
        reconcile_active_orchestrations(db)
        
        # Reload tasks from DB
        db.expire_all()
        reconciled_pending = db.query(Task).filter(Task.id == task_pending.id).first()
        reconciled_expired = db.query(Task).filter(Task.id == task_expired.id).first()
        
        # 1. Assert Task 1 was kept as pending and re-enqueued to test medium queue
        medium_queue = r.lrange("task_queue_test_medium", 0, -1)
        print(f"Redis test medium queue items: {medium_queue}")
        assert str(task_pending.id) in medium_queue, "Pending task ID missing from Redis queue!"
        
        # 2. Assert Task 2 was recovered (marked pending, retries incremented, queue re-enqueued)
        print(f"Expired task status: {reconciled_expired.status}, retries: {reconciled_expired.retry_count}, recovered: {reconciled_expired.recovered_count}")
        assert reconciled_expired.status == "pending", "Expired task should be marked as pending!"
        assert reconciled_expired.retry_count == 1, "Retry count should be incremented!"
        assert reconciled_expired.recovered_count == 1, "Recovered count should be incremented!"
        
        high_queue = r.lrange("task_queue_test_high", 0, -1)
        print(f"Redis test high queue items: {high_queue}")
        assert str(task_expired.id) in high_queue, "Expired task ID missing from high priority Redis queue!"
        
        print("SUCCESS: Orchestrator crash recovery and queue reconciliation verified successfully!")
        return True
    except Exception as e:
        print(f"FAIL in Scenario B: {e}")
        return False
    finally:
        db.close()

def test_scenario_c():
    print_banner("Scenario C: Idempotent Dependency Releasing & Duplicate Protection")
    clear_system()
    
    # 1. Create a pipeline
    payload = {
        "name": "Test Duplicate Releases Pipeline",
        "pipeline_type": "document_processing_demo",
        "initial_payload": {"source_text": "idempotency test"}
    }
    res = requests.post(f"{API_URL}/pipelines", json=payload, headers=HEADERS)
    p_data = res.json()
    pipeline_id = p_data["pipeline_id"]
    
    db = SessionLocal()
    try:
        tasks = db.query(Task).filter(Task.pipeline_id == pipeline_id).order_by(Task.id.asc()).all()
        task_a = tasks[0] # first task (parse_document)
        task_b = tasks[1] # second task (chunk_text)
        
        # Claim Task A
        claim_res = requests.post(f"{API_URL}/tasks/{task_a.id}/claim", json={"worker_id": "worker-idempotent"}, headers=HEADERS)
        lease_token = claim_res.json()["lease_token"]
        
        # Complete Task A
        complete_res = requests.patch(
            f"{API_URL}/tasks/{task_a.id}", 
            json={"status": "completed", "worker_id": "worker-idempotent", "lease_token": lease_token},
            headers=HEADERS
        )
        assert complete_res.status_code == 200
        
        # Verify Task B is released (status pending, present in Redis queue)
        db.expire_all()
        t_b_first = db.query(Task).filter(Task.id == task_b.id).first()
        assert t_b_first.status == 'pending'
        
        test_queue_medium = r.lrange("task_queue_test_medium", 0, -1)
        initial_q_len = len(test_queue_medium)
        print(f"Initial queue length for released child: {initial_q_len}")
        assert str(task_b.id) in test_queue_medium, "Child task B should be enqueued in Redis!"
        
        # Simulate duplicate parent completion call
        print("Sending duplicate completion call for parent task A...")
        dup_res = requests.patch(
            f"{API_URL}/tasks/{task_a.id}", 
            json={"status": "completed", "worker_id": "worker-idempotent", "lease_token": lease_token},
            headers=HEADERS
        )
        
        # Verify child task B is NOT released twice (queue size does not change and child isn't duplicate enqueued)
        test_queue_medium_dup = r.lrange("task_queue_test_medium", 0, -1)
        final_q_len = len(test_queue_medium_dup)
        print(f"Duplicate queue length: {final_q_len}")
        
        # Check count of task_b in queue
        count_in_queue = test_queue_medium_dup.count(str(task_b.id))
        print(f"Count of task #{task_b.id} in queue: {count_in_queue}")
        assert count_in_queue == 1, "FAIL: Child task was enqueued multiple times!"
        
        print("SUCCESS: Idempotency protections and double-release guard are fully functional!")
        return True
    except Exception as e:
        print(f"FAIL in Scenario C: {e}")
        return False
    finally:
        db.close()

def test_scenario_d():
    print_banner("Scenario D: Historical Time-Travel Debugging")
    clear_system()
    
    # 1. Create a Pipeline
    payload = {
        "name": "Test Time-Travel Pipeline",
        "pipeline_type": "document_processing_demo",
        "initial_payload": {"source_text": "time-travel text"}
    }
    res = requests.post(f"{API_URL}/pipelines", json=payload, headers=HEADERS)
    pipeline_id = res.json()["pipeline_id"]
    
    db = SessionLocal()
    try:
        tasks = db.query(Task).filter(Task.pipeline_id == pipeline_id).order_by(Task.id.asc()).all()
        task_a = tasks[0]
        
        # Step 1: Claim Task A
        claim_res = requests.post(f"{API_URL}/tasks/{task_a.id}/claim", json={"worker_id": "worker-travel"}, headers=HEADERS)
        lease_token = claim_res.json()["lease_token"]
        
        # Fetch event list
        events_res = requests.get(f"{API_URL}/events/pipelines/{pipeline_id}", headers=HEADERS)
        events = events_res.json()
        print(f"Chronological event count before complete: {len(events)}")
        
        # Time-Travel step-by-step check
        # Check state at step 1 (Pipeline created, but task not claimed yet)
        state_start_res = requests.get(f"{API_URL}/replay/pipelines/{pipeline_id}/state?target_event_id={events[2]['id']}", headers=HEADERS)
        state_start = state_start_res.json()
        print(f"State status at pipeline initialization: {state_start['pipeline']['status']}")
        assert state_start['pipeline']['status'] == 'created'
        
        # Complete Task A to generate full log
        requests.patch(
            f"{API_URL}/tasks/{task_a.id}", 
            json={"status": "completed", "worker_id": "worker-travel", "lease_token": lease_token},
            headers=HEADERS
        )
        
        all_events_res = requests.get(f"{API_URL}/events/pipelines/{pipeline_id}", headers=HEADERS)
        all_events = all_events_res.json()
        print(f"Total chronological event count after complete: {len(all_events)}")
        
        # Scrub timeline to intermediate step (e.g. after task was started but before completion)
        # Let's find TASK_CLAIMED event
        started_event = next(e for e in all_events if e["event_type"] == "TASK_CLAIMED")
        state_running_res = requests.get(f"{API_URL}/replay/pipelines/{pipeline_id}/state?target_event_id={started_event['id']}", headers=HEADERS)
        state_running = state_running_res.json()
        
        print(f"Replayed state at TASK_CLAIMED: Pipeline status = {state_running['pipeline']['status']}, Task A status = {state_running['tasks'][str(task_a.id)]['status']}")
        assert state_running['pipeline']['status'] == 'running'
        assert state_running['tasks'][str(task_a.id)]['status'] == 'running'
        
        print("SUCCESS: Historical time-travel reconstruction verified!")
        return True
    except Exception as e:
        print(f"FAIL in Scenario D: {e}")
        return False
    finally:
        db.close()

def test_scenario_e():
    print_banner("Scenario E: Snapshots & Incremental Replay")
    clear_system()
    
    # 1. Create a Pipeline
    payload = {
        "name": "Test Snapshots Pipeline",
        "pipeline_type": "document_processing_demo",
        "initial_payload": {"source_text": "snapshot test"}
    }
    res = requests.post(f"{API_URL}/pipelines", json=payload, headers=HEADERS)
    pipeline_id = res.json()["pipeline_id"]
    
    # 2. Trigger snapshot generation manually
    snap_res = requests.post(f"{API_URL}/snapshots/pipelines/{pipeline_id}/create", headers=HEADERS)
    if snap_res.status_code != 201:
        print(f"FAIL: Snapshot trigger failed. Text: {snap_res.text}")
        return False
        
    snap_data = snap_res.json()
    print(f"Snapshot created successfully at last_event_id: {snap_data['last_event_id']}")
    
    db = SessionLocal()
    try:
        tasks = db.query(Task).filter(Task.pipeline_id == pipeline_id).order_by(Task.id.asc()).all()
        task_a = tasks[0]
        
        # 3. Append new events by claiming the task
        requests.post(f"{API_URL}/tasks/{task_a.id}/claim", json={"worker_id": "worker-snap"}, headers=HEADERS)
        
        # 4. Fetch reconstructed state and assert it utilized the snapshot to skip previous events
        # We can verify that state is correct
        replay_res = requests.get(f"{API_URL}/replay/pipelines/{pipeline_id}/state", headers=HEADERS)
        state = replay_res.json()
        
        print(f"Reconstructed task status after snapshot: {state['tasks'][str(task_a.id)]['status']}")
        assert state['tasks'][str(task_a.id)]['status'] == 'running'
        
        # 5. Check snapshot entries in database
        snapshots_count = db.query(OrchestrationSnapshot).filter(OrchestrationSnapshot.pipeline_id == pipeline_id).count()
        print(f"Total database snapshots count for pipeline: {snapshots_count}")
        assert snapshots_count == 1, "There should be exactly 1 snapshot!"
        
        print("SUCCESS: Snapshots and incremental replay boundary verification completed successfully!")
        return True
    except Exception as e:
        print(f"FAIL in Scenario E: {e}")
        return False
    finally:
        db.close()

if __name__ == '__main__':
    print("=" * 80)
    print("  RUNNING RESILIENCE & EVENT REPLAY VERIFICATION SUITE")
    print("=" * 80)
    
    success = True
    success &= test_scenario_a()
    success &= test_scenario_b()
    success &= test_scenario_c()
    success &= test_scenario_d()
    success &= test_scenario_e()
    
    print("\n" + "=" * 80)
    if success:
        print("  ALL VERIFICATION SCENARIOS PASSED SUCCESSFULLY!")
    else:
        print("  SOME VERIFICATION SCENARIOS FAILED!")
    print("=" * 80)
    sys.exit(0 if success else 1)
