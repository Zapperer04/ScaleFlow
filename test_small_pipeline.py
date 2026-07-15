import requests
import time
import sys

API_URL = "http://localhost:5000"
HEADERS = {
    "X-API-Key": "local_only_secret_key",
    "Content-Type": "application/json"
}

def run_test():
    print("--- Starting Stage 3: Small Pipeline Test ---")
    payload = {
        "name": "Stage 3 Test Pipeline",
        "pipeline_type": "test_small_pipeline",
        "initial_payload": {
            "report_type": "monthly_summary",
            "to": "dev@scaleflow.io"
        }
    }
    
    # 1. Create pipeline
    r = requests.post(f"{API_URL}/pipelines", json=payload, headers=HEADERS)
    if r.status_code not in [200, 201]:
        print(f"Failed to create pipeline: {r.status_code} - {r.text}")
        sys.exit(1)
        
    pipeline_id = r.json()["pipeline_id"]
    print(f"Pipeline created successfully. ID: {pipeline_id}")
    
    # 2. Poll status
    time_limit = 60 # 60 seconds max
    start_time = time.time()
    last_status = None
    
    while time.time() - start_time < time_limit:
        r = requests.get(f"{API_URL}/pipelines/{pipeline_id}", headers=HEADERS)
        if r.status_code != 200:
            print(f"Failed to get pipeline status: {r.status_code}")
            time.sleep(1)
            continue
            
        data = r.json()
        status = data["pipeline"]["status"]
        tasks = data.get("tasks", [])
        
        # Format task statuses
        task_info = ", ".join([f"{t['id']} ({t['status']})" for t in tasks])
        
        if (status, task_info) != last_status:
            print(f"[{int(time.time() - start_time)}s] Pipeline Status: {status} | Tasks: {task_info}")
            last_status = (status, task_info)
            
        if status in ["completed", "failed", "cancelled"]:
            if status == "completed":
                print("Stage 3: SUCCESS!")
                return
            else:
                print(f"Stage 3: FAILED with status {status}")
                sys.exit(1)
                
        time.sleep(1)
        
    print("Stage 3: FAILED (Timeout)")
    sys.exit(1)

if __name__ == "__main__":
    run_test()
