import os
import sys
import time
import json
import requests
import redis
import traceback
from datetime import datetime, timedelta
from sqlalchemy import text

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
from models import SessionLocal, Task, TaskDependency, TaskLog, Pipeline, Artifact, FileRecord, OrchestrationEvent, OrchestrationSnapshot, OrchestratorInstance, WorkerRegistry
from app import scan_and_unblock_deferred_tasks

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
        db.query(OrchestratorInstance).delete()
        db.query(WorkerRegistry).delete()
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
    r.delete("scaleflow:leader_lock")
    print("System cleared successfully.")

def test_scenario_a():
    print_banner("Scenario A: Orchestrator Lease Takeover & Recovery")
    clear_system()
    db = SessionLocal()
    
    try:
        # 1. Create a Pipeline
        payload = {
            "name": "Test HA Takeover Pipeline",
            "pipeline_type": "document_processing_demo",
            "initial_payload": {
                "source_text": "HA Takeover simulation"
            }
        }
        res = requests.post(f"{API_URL}/pipelines", json=payload, headers=HEADERS)
        if res.status_code not in [200, 201]:
            print(f"FAIL: Failed to create pipeline. Code: {res.status_code}, Text: {res.text}")
            return False
            
        p_data = res.json()
        pipeline_id = p_data["pipeline_id"]
        print(f"Pipeline #{pipeline_id} created.")
        
        # Verify it has been claimed by the default running orchestrator instance
        db.expire_all()
        pipe = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
        initial_owner = pipe.owner_instance_id
        initial_version = pipe.ownership_version
        print(f"Initial owner: {initial_owner}, Version token: {initial_version}")
        
        if not initial_owner:
            print("FAIL: Pipeline was not claimed initially.")
            return False

        # 2. Simulate Orchestrator A death by expiring its lease in the database
        print("Simulating owner crash (expiring lease in DB)...")
        pipe.owner_lease_expires_at = datetime.now() - timedelta(seconds=1)
        db.commit()
        
        # 3. Trigger ownership takeover sweep on a mock orchestrator instance (Orchestrator B)
        print("Running takeover sweep on Orchestrator B...")
        from services.ha_coordinator_service import HACoordinator
        coord_b = HACoordinator()
        coord_b.instance_id = "orchestrator-B"
        coord_b.register_instance()
        coord_b._claim_active_pipelines(db)
        
        # 4. Assert that Orchestrator B assumed ownership and incremented fencing token version
        db.expire_all()
        db.refresh(pipe)
        print(f"New owner in DB: {pipe.owner_instance_id}, New version token: {pipe.ownership_version}")
        
        if pipe.owner_instance_id != "orchestrator-B":
            print(f"FAIL: Ownership was not transferred. Current owner: {pipe.owner_instance_id}")
            return False
            
        if pipe.ownership_version != initial_version + 1:
            print(f"FAIL: Fencing token was not incremented. Version: {pipe.ownership_version}")
            return False
            
        # Verify event sourcing logged the takeover event
        takeover_event = db.query(OrchestrationEvent).filter(
            OrchestrationEvent.pipeline_id == pipeline_id,
            OrchestrationEvent.event_type == 'PIPELINE_OWNERSHIP_TAKEN_OVER'
        ).first()
        if not takeover_event:
            print("FAIL: Event sourcing takeover log event was not published.")
            return False
        print(f"SUCCESS: Takeover event published: {takeover_event.message}")
        
        return True
    except Exception as e:
        print(f"Scenario A EXCEPTION: {e}")
        traceback.print_exc()
        return False
    finally:
        db.close()

def test_scenario_b():
    print_banner("Scenario B: Split-Brain Prevention via Fencing Token Validation")
    clear_system()
    db = SessionLocal()
    
    try:
        # 1. Create a Pipeline and Task
        payload = {
            "name": "Test Split-Brain Fencing",
            "pipeline_type": "document_processing_demo",
            "initial_payload": {
                "source_text": "Fencing simulation"
            }
        }
        res = requests.post(f"{API_URL}/pipelines", json=payload, headers=HEADERS)
        p_data = res.json()
        pipeline_id = p_data["pipeline_id"]
        
        print("Waiting 2.5s for background coordinator to claim pipeline lease...")
        time.sleep(2.5)
        
        # Get first task
        db.expire_all()
        task = db.query(Task).filter(Task.pipeline_id == pipeline_id).first()
        print(f"Task #{task.id} created for pipeline #{pipeline_id}.")
        
        # Claim task
        claim_res = requests.post(f"{API_URL}/tasks/{task.id}/claim", json={"worker_id": "worker-A"}, headers=HEADERS)
        if claim_res.status_code != 200:
            print(f"FAIL: Task claim failed! Status: {claim_res.status_code}, Body: {claim_res.text}")
            return False
        lease_token = claim_res.json()["lease_token"]
        
        # 2. Simulate local cache ownership token is 1 (Orchestrator A)
        import services.ha_coordinator_service
        services.ha_coordinator_service.owned_pipelines_versions[pipeline_id] = 1
        
        # 3. Simulate another coordinator (Orchestrator B) taking over in the DB (incrementing DB version to 2)
        print("Simulating takeover: updating ownership version in database to 2...")
        db.execute(text("UPDATE pipelines SET ownership_version = 2 WHERE id = :pid"), {"pid": pipeline_id})
        db.commit()
        
        # 4. Attempt to complete task on Orchestrator A. Should raise a 409 fencing conflict!
        print("Worker attempting status patch update on hijacked pipeline...")
        patch_res = requests.patch(
            f"{API_URL}/tasks/{task.id}", 
            json={
                "status": "completed",
                "worker_id": "worker-A",
                "lease_token": lease_token
            },
            headers=HEADERS
        )
        print(f"PATCH status code: {patch_res.status_code}, Response: {patch_res.text}")
        
        if patch_res.status_code != 409:
            print(f"FAIL: Expected 409 conflict, got {patch_res.status_code}")
            return False
            
        if "Fencing conflict" not in patch_res.json().get("error", ""):
            print(f"FAIL: Unexpected error message: {patch_res.json()}")
            return False
            
        print("SUCCESS: Split-brain status update rejected with 409 Version Conflict!")
        
        # 5. Attempt task lease renewal on hijacked pipeline. Should also raise a 409 fencing conflict!
        print("Worker attempting lease renewal on hijacked pipeline...")
        renew_res = requests.post(
            f"{API_URL}/tasks/{task.id}/renew-lease", 
            json={
                "worker_id": "worker-A",
                "lease_token": lease_token,
                "extend_by_seconds": 30
            },
            headers=HEADERS
        )
        print(f"Renew status code: {renew_res.status_code}, Response: {renew_res.text}")
        
        if renew_res.status_code != 409:
            print(f"FAIL: Expected 409 for lease renewal, got {renew_res.status_code}")
            return False
            
        print("SUCCESS: Split-brain lease renewal rejected with 409 Version Conflict!")
        return True
    except Exception as e:
        print(f"Scenario B EXCEPTION: {e}")
        traceback.print_exc()
        return False
    finally:
        db.close()

def test_scenario_c():
    print_banner("Scenario C: Capability-Aware Routing & Starvation Protection")
    clear_system()
    db = SessionLocal()
    
    try:
        # Register capability workers
        print("Registering workers with specific capability profiles...")
        requests.post(f"{API_URL}/workers/register", json={
            "worker_id": "worker-gpu-1",
            "capabilities": ["embedding_gpu"],
            "resource_limits": {"gpu_memory": "16GB"}
        }, headers=HEADERS)
        
        requests.post(f"{API_URL}/workers/register", json={
            "worker_id": "worker-cpu-1",
            "capabilities": ["cpu_heavy"],
            "resource_limits": {"cpu_cores": 8}
        }, headers=HEADERS)
        
        # Verify they are stored in the DB registry
        db.expire_all()
        registrations = db.query(WorkerRegistry).all()
        print(f"Registered workers in DB: {[w.worker_id for w in registrations]}")
        
        # Enqueue two tasks: one GPU-heavy (generate_embeddings) and one CPU-heavy (parse_document)
        print("Simulating task creation...")
        gpu_task = Task(type="generate_embeddings", data=json.dumps({}), priority="medium", status="pending")
        cpu_task = Task(type="parse_document", data=json.dumps({}), priority="medium", status="pending")
        db.add(gpu_task)
        db.add(cpu_task)
        db.commit()
        
        # Use dependency_resolver enqueue_task
        from orchestrator.dependency_resolver import enqueue_task
        enqueue_task(db, gpu_task)
        enqueue_task(db, cpu_task)
        db.commit()
        
        # Assert tasks are in their capability-specific queues
        print("Verifying Redis queue routing...")
        gpu_queue = "task_queue_embedding_gpu_medium"
        cpu_queue = "task_queue_cpu_heavy_medium"
        
        gpu_backlog = r.llen(gpu_queue) or 0
        cpu_backlog = r.llen(cpu_queue) or 0
        print(f"GPU Queue size: {gpu_backlog}, CPU Queue size: {cpu_backlog}")
        
        if gpu_backlog == 0 or cpu_backlog == 0:
            print("FAIL: Tasks were not enqueued into capability queues.")
            return False
            
        # Simulate worker.py popping tasks
        import worker
        
        # Mock Worker 1: GPU capabilities only
        worker.WORKER_ID = "worker-gpu-1"
        worker.WORKER_CAPABILITIES = ["embedding_gpu"]
        worker.ALL_WORKER_QUEUES = [gpu_queue]
        
        gpu_pop = worker.get_next_task()
        print(f"GPU Worker popped task: {gpu_pop}")
        if not gpu_pop or gpu_pop[1] != str(gpu_task.id):
            print(f"FAIL: GPU Worker popped wrong task. Expected {gpu_task.id}, got {gpu_pop}")
            return False
            
        # Mock Worker 2: CPU capabilities only
        worker.WORKER_ID = "worker-cpu-1"
        worker.WORKER_CAPABILITIES = ["cpu_heavy"]
        worker.ALL_WORKER_QUEUES = [cpu_queue]
        
        cpu_pop = worker.get_next_task()
        print(f"CPU Worker popped task: {cpu_pop}")
        if not cpu_pop or cpu_pop[1] != str(cpu_task.id):
            print(f"FAIL: CPU Worker popped wrong task. Expected {cpu_task.id}, got {cpu_pop}")
            return False
            
        print("SUCCESS: Capability-aware task routing and polling verified!")
        return True
    except Exception as e:
        print(f"Scenario C EXCEPTION: {e}")
        traceback.print_exc()
        return False
    finally:
        db.close()

def test_scenario_d():
    print_banner("Scenario D: Upstream Congestion Cascades & Backpressure Unblocking")
    clear_system()
    db = SessionLocal()
    
    try:
        # 1. Artificially saturate the summarization queue (capability queue for summarize_document)
        congested_queue = "task_queue_summarization_llm_medium"
        congested_test_queue = "task_queue_test_summarization_llm_medium"
        print("Saturating downstream queue to simulate congestion...")
        r.lpush(congested_queue, *[990 + i for i in range(12)]) # 12 dummy items (> 10 limit)
        r.lpush(congested_test_queue, *[990 + i for i in range(12)]) # 12 dummy items (> 10 limit)
        
        # 2. Create a pipeline with dependencies: Parse Document -> Summarize Document
        # To do this cleanly, create a pipeline
        payload = {
            "name": "Test Congestion Cascades",
            "pipeline_type": "document_processing_demo",
            "initial_payload": {
                "source_text": "Congestion stress test"
            }
        }
        res = requests.post(f"{API_URL}/pipelines", json=payload, headers=HEADERS)
        p_data = res.json()
        pipeline_id = p_data["pipeline_id"]
        
        print("Waiting 2.5s for background coordinator to claim pipeline lease...")
        time.sleep(2.5)
        
        # Ensure our local coordinator owns it so fencing doesn't block updates
        db.expire_all()
        pipe = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
        import services.ha_coordinator_service
        services.ha_coordinator_service.owned_pipelines_versions[pipeline_id] = pipe.ownership_version
        
        # Get the first task (parse_document) and second task (chunk_text, which depends on parse_document, wait, check template)
        # Looking at template, Document Processing Demo nodes are:
        # parse_document -> chunk_text -> generate_embeddings -> summarize_document
        # Let's change summarize_document to depend on chunk_text directly, or just trace task completions:
        # If we complete generate_embeddings, the downstream summarize_document is released.
        # Let's find generate_embeddings task and complete it.
        # First, complete preceding tasks to reach generate_embeddings
        tasks = db.query(Task).filter(Task.pipeline_id == pipeline_id).order_by(Task.id.asc()).all()
        
        # Complete parse_document, chunk_text, generate_embeddings tasks
        worker_id = "worker-ha"
        for t in tasks:
            if t.type == "summarize_document":
                # This is the target downstream task that should get blocked!
                continue
                
            # Claim
            claim_res = requests.post(f"{API_URL}/tasks/{t.id}/claim", json={"worker_id": worker_id}, headers=HEADERS)
            if claim_res.status_code != 200:
                print(f"FAIL: Task claim in Scenario D failed for task #{t.id}! Status: {claim_res.status_code}, Body: {claim_res.text}")
                return False
            lease_token = claim_res.json()["lease_token"]
            
            # Complete
            requests.patch(
                f"{API_URL}/tasks/{t.id}", 
                json={
                    "status": "completed",
                    "worker_id": worker_id,
                    "lease_token": lease_token
                },
                headers=HEADERS
            )
            print(f"Task #{t.id} ({t.type}) completed.")
            
        # 3. Assert that the summarize_document task gets throttled and marked as blocked due to upstream congestion!
        db.expire_all()
        summarize_task = db.query(Task).filter(Task.pipeline_id == pipeline_id, Task.type == "summarize_document").first()
        print(f"Downstream task status: {summarize_task.status}, Blocked reason: {summarize_task.blocked_reason}")
        
        if summarize_task.status != "blocked" or summarize_task.blocked_reason != "Upstream congestion: throttled":
            print(f"FAIL: Downstream task was not throttled. Status: {summarize_task.status}, Reason: {summarize_task.blocked_reason}")
            return False
            
        print("SUCCESS: Upstream backpressure congestion cascade verified! Task is blocked.")
        
        # 4. Clear/drain the congestion queue
        print("Draining saturated queue...")
        r.delete(congested_queue)
        r.delete(congested_test_queue)
        
        # 5. Run the unblock scanner to release the throttled task
        print("Running unblock scanner...")
        scan_and_unblock_deferred_tasks(db)
        db.commit()
        
        # 6. Assert that summarize_document task is now pending and released into the capability queue
        db.expire_all()
        db.refresh(summarize_task)
        print(f"Downstream task status after scan: {summarize_task.status}")
        
        if summarize_task.status != "pending" or summarize_task.blocked_reason is not None:
            print(f"FAIL: Task was not unblocked. Status: {summarize_task.status}")
            return False
            
        summarize_backlog = (r.llen("task_queue_summarization_llm_medium") or 0) + (r.llen("task_queue_test_summarization_llm_medium") or 0)
        print(f"Summarization queue backlog: {summarize_backlog}")
        
        if summarize_backlog == 0:
            print("FAIL: Task was not enqueued after unblocking.")
            return False
            
        print("SUCCESS: Backpressure unblock successfully verified!")
        return True
    except Exception as e:
        print(f"Scenario D EXCEPTION: {e}")
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 80)
    print("  RUNNING SCALEFLOW PHASE 8 HA CHAOS & RELIABILITY SIMULATION SUITE")
    print("=" * 80)
    
    results = {}
    
    # Enable HA Coordinator mode flags locally
    import services.ha_coordinator_service
    services.ha_coordinator_service.is_leader_instance = True
    
    try:
        results["Scenario A (HA Takeover)"] = test_scenario_a()
        results["Scenario B (Split-Brain Fencing)"] = test_scenario_b()
        results["Scenario C (Capability Routing)"] = test_scenario_c()
        results["Scenario D (Backpressure Cascade)"] = test_scenario_d()
    except Exception as e:
        print(f"Global simulation suite crash: {e}")
        traceback.print_exc()
        
    print_banner("SIMULATION RESULTS SUMMARY")
    all_passed = True
    for scenario, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        if not passed:
            all_passed = False
        print(f"  {scenario:<45}: {status}")
    print("=" * 80)
    
    if all_passed:
        print("  ALL CHAOS FAILURE SUITE SIMULATIONS VERIFIED CORRECTLY! PRODUCTION-GRADE READY.")
        print("=" * 80)
        sys.exit(0)
    else:
        print("  CHAOS FAILURE SUITE SIMULATIONS REPORTED FAILURES. FIX THE COMPONENT CORRECTNESS.")
        print("=" * 80)
        sys.exit(1)
