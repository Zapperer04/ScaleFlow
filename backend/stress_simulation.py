import os
import sys
import time
import json
import requests
import redis
import subprocess
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
from models import SessionLocal, Task, TaskDependency, TaskLog, Pipeline, Artifact, FileRecord
from worker import get_next_task

def run_cmd(args):
    print(f"Running command: {' '.join(args)}")
    res = subprocess.run(args, capture_output=True, text=True)
    return res.returncode == 0, res.stdout, res.stderr

def print_banner(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def clear_system():
    print("Cleaning database and Redis queues...")
    db = SessionLocal()
    try:
        from models import OrchestrationEvent, OrchestrationSnapshot
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
    r = redis.Redis(host=os.environ.get("REDIS_HOST", "localhost"), port=int(os.environ.get("REDIS_PORT", 6379)), decode_responses=True)
    for q in r.keys("task_queue_*"):
        r.delete(q)
    r.delete("wrr_index")
    print("System cleared successfully.")

def test_scenario_a():
    print_banner("Scenario A: Burst Load & Backpressure Deferral")
    
    # 1. Stop workers
    print("Stopping worker containers...")
    run_cmd(["docker", "compose", "stop", "worker1", "worker2", "worker3"])
    
    # 2. Clear system
    clear_system()
    
    # 3. Create 50 high priority tasks (they bypass backpressure and populate backlog)
    print("Enqueuing 50 high-priority tasks to saturate the queue backlog...")
    tasks_created = []
    for i in range(50):
        payload = {
            "type": "send_email",
            "priority": "high",
            "data": {
                "to": f"user{i}@example.com",
                "subject": f"High Priority Task {i}",
                "body": "This is a stress test task"
            }
        }
        res = requests.post(f"{API_URL}/tasks", json=payload, headers=HEADERS)
        if res.status_code != 201:
            print(f"Failed to create high priority task: {res.text}")
            return False
        tasks_created.append(res.json()["id"])
        
    print(f"Successfully enqueued 50 high-priority tasks.")

    # Check backpressure status via API
    res_bp = requests.get(f"{API_URL}/metrics/backpressure", headers=HEADERS)
    if res_bp.status_code == 200:
        bp_info = res_bp.json()
        print(f"Backpressure State: active={bp_info.get('backpressure_active')}, health={bp_info.get('system_health')}, backlog={bp_info.get('config', {}).get('max_backlog_size')}")
        assert bp_info.get("backpressure_active") == True, "Backpressure should be active!"
    else:
        print(f"Failed to fetch backpressure metrics: {res_bp.text}")
        return False

    # 4. Attempt to create a low-priority and medium-priority task (should be deferred)
    print("Enqueuing low and medium priority tasks under active backpressure...")
    
    payload_med = {
        "type": "send_email",
        "priority": "medium",
        "data": {
            "to": "med@example.com",
            "subject": "Medium Priority",
            "body": "Should be deferred"
        }
    }
    res_med = requests.post(f"{API_URL}/tasks", json=payload_med, headers=HEADERS)
    
    payload_low = {
        "type": "send_email",
        "priority": "low",
        "data": {
            "to": "low@example.com",
            "subject": "Low Priority",
            "body": "Should be deferred"
        }
    }
    res_low = requests.post(f"{API_URL}/tasks", json=payload_low, headers=HEADERS)
    
    if res_med.status_code != 201 or res_low.status_code != 201:
        print(f"Failed to create tasks under backpressure: med={res_med.text}, low={res_low.text}")
        return False
        
    med_id = res_med.json()["id"]
    low_id = res_low.json()["id"]
    
    # Query status in database
    db = SessionLocal()
    try:
        t_med = db.query(Task).filter(Task.id == med_id).first()
        t_low = db.query(Task).filter(Task.id == low_id).first()
        
        print(f"Medium Task status: {t_med.status}, blocked_reason: {t_med.blocked_reason}")
        print(f"Low Task status: {t_low.status}, blocked_reason: {t_low.blocked_reason}")
        
        assert t_med.status == "blocked", "Medium task should be blocked!"
        assert "backpressure" in t_med.blocked_reason, "Should be blocked due to backpressure!"
        assert t_low.status == "blocked", "Low task should be blocked!"
        assert "backpressure" in t_low.blocked_reason, "Should be blocked due to backpressure!"
        
    finally:
        db.close()
        
    print("Scenario A SUCCESS: Backpressure deferral verified.")
    return True

def test_scenario_b():
    print_banner("Scenario B: Worker Crash & Recovery (Lease Expiration & Stale Updates)")
    
    # 1. Clear system
    clear_system()
    
    # 2. Enqueue a task
    print("Creating a task to claim and simulate worker crash...")
    payload = {
        "type": "send_email",
        "priority": "high",
        "data": {
            "to": "test@example.com",
            "subject": "Lease Test",
            "body": "Testing lease recovery"
        }
    }
    res = requests.post(f"{API_URL}/tasks", json=payload, headers=HEADERS)
    if res.status_code != 201:
        print(f"Failed to create task: {res.text}")
        return False
    task_id = res.json()["id"]
    
    # 3. Claim task manually
    print(f"Claiming task #{task_id} as 'worker-mock-1'...")
    res_claim = requests.post(f"{API_URL}/tasks/{task_id}/claim", json={"worker_id": "worker-mock-1"}, headers=HEADERS)
    if res_claim.status_code != 200:
        print(f"Failed to claim task: {res_claim.text}")
        return False
        
    claimed_task = res_claim.json()
    lease_token = claimed_task["lease_token"]
    print(f"Claimed task lease token: {lease_token}")
    
    # 4. Backdate lease in DB to force expiration (lease duration is 10s or 30s, backdate by 10 minutes)
    print("Backdating lease start time to force expiration...")
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        task.started_at = datetime.now() - timedelta(minutes=10)
        task.lease_expires_at = datetime.now() - timedelta(minutes=5)
        db.commit()
    finally:
        db.close()
        
    # 5. Let the recovery scanner pick it up. The app.py background recovery thread runs every 10s.
    print("Waiting 12 seconds for recovery scanner to run...")
    time.sleep(12)
    
    # Check task state in DB
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        print(f"Task status after recovery scan: {task.status}, recovered_count: {task.recovered_count}")
        assert task.status == 'pending', "Task should be recovered and set back to pending!"
        assert task.recovered_count == 1, "Task recovered_count should be 1!"
    finally:
        db.close()
        
    # 6. Simulate worker-mock-1 waking up and trying to complete the task with stale token
    print("Simulating crashed worker attempting to update task with stale token...")
    payload_update = {
        "status": "completed",
        "worker_id": "worker-mock-1",
        "lease_token": lease_token
    }
    res_update = requests.patch(f"{API_URL}/tasks/{task_id}", json=payload_update, headers=HEADERS)
    print(f"Response status: {res_update.status_code}, body: {res_update.text}")
    assert res_update.status_code == 409, "Stale update should return 409 Conflict!"
    assert "Stale worker update rejected" in res_update.json()["error"], "Should reject with stale worker error message!"
    
    # Verify stale incident log is registered
    db = SessionLocal()
    try:
        logs = db.query(TaskLog).filter(TaskLog.task_id == task_id, TaskLog.event_type == 'stale_worker_update_rejected').all()
        print(f"Found {len(logs)} stale worker rejection logs in DB.")
        assert len(logs) > 0, "Stale worker log should be written!"
    finally:
        db.close()
        
    print("Scenario B SUCCESS: Worker crash recovery and stale rejection verified.")
    return True

def test_scenario_c():
    print_banner("Scenario C: Starvation Prevention & Weighted Round-Robin Scheduling")
    
    # 1. Clear system
    clear_system()
    
    # 2. Populate 15 tasks in each queue
    print("Enqueueing 15 tasks of high, medium, and low priority...")
    for priority in ['high', 'medium', 'low']:
        for i in range(15):
            payload = {
                "type": "send_email",
                "priority": priority,
                "data": {
                    "to": f"{priority}_{i}@example.com",
                    "subject": f"WRR Test {priority} {i}",
                    "body": "WRR testing"
                }
            }
            res = requests.post(f"{API_URL}/tasks", json=payload, headers=HEADERS)
            if res.status_code != 201:
                print(f"Failed to create task: {res.text}")
                return False
                
    # 3. Simulate sequential claims using get_next_task() from worker
    # We will call get_next_task() 10 times to verify the modulo 10 cycle ratio
    print("Simulating 10 worker task pops sequentially...")
    popped_priorities = []
    for _ in range(10):
        res = get_next_task()
        if res:
            queue_name, val = res
            # Extract priority from queue name
            priority = queue_name.split("_")[-1]
            popped_priorities.append(priority)
            
    print(f"Priorities popped in 10-step cycle: {popped_priorities}")
    
    # Count occurrences
    high_count = popped_priorities.count("high")
    med_count = popped_priorities.count("medium")
    low_count = popped_priorities.count("low")
    
    print(f"WRR results: High={high_count}, Medium={med_count}, Low={low_count}")
    
    # Assert that all queues received slot allocations according to ratio (6:3:1)
    assert high_count == 6, f"Expected 6 High tasks in modulo 10 cycle, got {high_count}"
    assert med_count == 3, f"Expected 3 Medium tasks in modulo 10 cycle, got {med_count}"
    assert low_count == 1, f"Expected 1 Low task in modulo 10 cycle, got {low_count}"
    
    print("Scenario C SUCCESS: WRR starvation prevention verified.")
    return True

def test_scenario_d():
    print_banner("Scenario D: Scaling recommendations & Queue Pressure Forecasting")
    
    # 1. Clear system
    clear_system()
    
    # 2. Enqueue 80 high priority tasks
    print("Enqueuing 80 high-priority tasks...")
    for i in range(80):
        payload = {
            "type": "send_email",
            "priority": "high",
            "data": {
                "to": f"scale{i}@example.com",
                "subject": f"Scale Test {i}",
                "body": "Saturating queue for scaling test"
            }
        }
        res = requests.post(f"{API_URL}/tasks", json=payload, headers=HEADERS)
        if res.status_code != 201:
            print(f"Failed to create task: {res.text}")
            return False
            
    # 3. Fetch scaling metrics from backend API
    print("Fetching scaling recommendation metrics...")
    res_scale = requests.get(f"{API_URL}/metrics/scaling", headers=HEADERS)
    if res_scale.status_code != 200:
        print(f"Failed to fetch scaling metrics: {res_scale.text}")
        return False
        
    scaling_data = res_scale.json()
    print(f"Scaling data returned: {json.dumps(scaling_data, indent=2)}")
    
    # Verification
    # Formula: recommended = math.ceil(R_in * T_exec + backlog * T_exec / T_target)
    # R_in = 0 (no new enqueue events in last 60s since they finished)
    # T_exec = 1.5 (default)
    # backlog = 80
    # T_target = 30.0
    # Recommended = 80 * 1.5 / 30 = 4.0
    recommended_workers = scaling_data.get("recommended_workers")
    print(f"Recommended workers: {recommended_workers} (Expected: 3-8)")
    assert 3 <= recommended_workers <= 8, f"Expected recommended workers to be between 3 and 8, got {recommended_workers}"
    
    print("Scenario D SUCCESS: Scaling recommendations and drain forecasts verified.")
    return True

def test_unblock_scanner():
    print_banner("Testing Unblock Scanner & Deferred Priority Aging")
    
    # 1. Clear system
    clear_system()
    
    # 2. Create a deferred task with deferred_at backdated to > 60s ago
    print("Creating backdated deferred task to test priority aging...")
    db = SessionLocal()
    try:
        task = Task(
            type="send_email",
            priority="low",
            status="blocked",
            blocked_reason="System overload backpressure: deferred",
            data=json.dumps({
                "to": "age@example.com",
                "subject": "Aging Test",
                "body": "Should escalate to high and release"
            }),
            deferred_at=datetime.now() - timedelta(seconds=70),
            created_at=datetime.now() - timedelta(seconds=70)
        )
        db.add(task)
        db.commit()
        task_id = task.id
    finally:
        db.close()
        
    print(f"Created backdated deferred task #{task_id}.")
    
    # 3. Wait for the unblock scanner to execute (runs every 5s)
    print("Waiting 7 seconds for unblock scanner to check and escalate...")
    time.sleep(7)
    
    # 4. Check DB status
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        print(f"Aged Task status: {task.status}, priority: {task.priority}")
        assert task.status == 'pending', "Aged task should be pending!"
        assert task.priority == 'high', "Aged task priority should be escalated to high!"
        
        # Verify log entry
        logs = db.query(TaskLog).filter(TaskLog.task_id == task_id, TaskLog.event_type == 'task_queued').all()
        print(f"Found {len(logs)} queue logs in DB for task #{task_id}.")
        assert any("Priority escalated to HIGH" in log.message for log in logs), "Should have escalation log entry!"
    finally:
        db.close()
        
    print("Deferred priority aging SUCCESS.")
    
    # Clear system to ensure backlog is 0 and system is healthy (even with 0 workers)
    clear_system()
    
    # 5. Create a deferred task under normal load to test safe release
    print("Creating deferred task under normal load...")
    db = SessionLocal()
    try:
        task2 = Task(
            type="send_email",
            priority="low",
            status="blocked",
            blocked_reason="System overload backpressure: deferred",
            data=json.dumps({
                "to": "release@example.com",
                "subject": "Release Test",
                "body": "Should release with low priority"
            }),
            deferred_at=datetime.now(),
            created_at=datetime.now()
        )
        db.add(task2)
        db.commit()
        task_id2 = task2.id
    finally:
        db.close()
        
    print(f"Created deferred task #{task_id2} with current timestamp.")
    
    # 6. Wait for unblock scanner to check and release (normal load since backlog is 0)
    print("Waiting 7 seconds for unblock scanner to check and release...")
    time.sleep(7)
    
    # 7. Check DB status
    db = SessionLocal()
    try:
        task2 = db.query(Task).filter(Task.id == task_id2).first()
        print(f"Released Task status: {task2.status}, priority: {task2.priority}")
        assert task2.status == 'pending', "Deferred task under normal load should be released!"
        assert task2.priority == 'low', "Deferred task should retain low priority!"
    finally:
        db.close()
        
    print("Normal load deferral release SUCCESS.")
    return True

def main():
    print_banner("STARTING INTEGRATION & STRESS SIMULATION SUITE")
    
    results = {}
    success = True
    
    try:
        results["Scenario A (Burst Load & Backpressure)"] = test_scenario_a()
    except Exception as e:
        print(f"Scenario A ERROR: {e}")
        import traceback; traceback.print_exc()
        results["Scenario A (Burst Load & Backpressure)"] = False
        
    try:
        results["Scenario B (Worker Crash & Recovery)"] = test_scenario_b()
    except Exception as e:
        print(f"Scenario B ERROR: {e}")
        import traceback; traceback.print_exc()
        results["Scenario B (Worker Crash & Recovery)"] = False
        
    try:
        results["Scenario C (Starvation Prevention)"] = test_scenario_c()
    except Exception as e:
        print(f"Scenario C ERROR: {e}")
        import traceback; traceback.print_exc()
        results["Scenario C (Starvation Prevention)"] = False
        
    try:
        results["Scenario D (Scaling & Forecasting)"] = test_scenario_d()
    except Exception as e:
        print(f"Scenario D ERROR: {e}")
        import traceback; traceback.print_exc()
        results["Scenario D (Scaling & Forecasting)"] = False

    try:
        results["Priority Escalation & Deferral Release"] = test_unblock_scanner()
    except Exception as e:
        print(f"Unblock scanner test ERROR: {e}")
        import traceback; traceback.print_exc()
        results["Priority Escalation & Deferral Release"] = False
        
    print_banner("SUMMARY OF TEST RESULTS")
    for name, res in results.items():
        color = "\033[92m" if res else "\033[91m"
        status = "SUCCESS" if res else "FAILED"
        reset = "\033[0m"
        print(f"[{color}{status}{reset}] {name}")
        if not res:
            success = False
            
    # Write to verification_results.json
    results_path = "verification_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Dumped results to {results_path}")
    
    # Restart workers
    print("\nRestarting workers to restore environment...")
    run_cmd(["docker", "compose", "start", "worker1", "worker2", "worker3"])
    
    if not success:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
