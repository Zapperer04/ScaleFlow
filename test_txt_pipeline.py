import os
import time
import requests

# Try to load env variables first
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))
try:
    import config
    API_URL = os.getenv("API_URL", "http://127.0.0.1:5000")
    API_KEY = os.getenv("API_KEY", "dev_secret_api_key")
except ImportError:
    API_URL = os.getenv("API_URL", "http://127.0.0.1:5000")
    API_KEY = os.getenv("API_KEY", "dev_secret_api_key")

HEADERS = {"X-API-Key": API_KEY}

def run_test():
    print("Waiting for backend to become healthy...")
    for _ in range(150):
        try:
            res = requests.get(f"{API_URL}/task-types")
            if res.status_code == 200:
                print("Backend is healthy!")
                break
        except Exception:
            pass
        time.sleep(2)
    else:
        print("Backend did not become healthy in time.")
        return

    # 1. Create a simple txt file
    with open("test_document.txt", "w") as f:
        f.write("This is a simple test document for the golden pipeline. It contains some text about deterministic execution.\nWe are testing the ingestion flow to prove it works reliably.")

    # 2. Upload the file
    print("Uploading text file...")
    with open("test_document.txt", "rb") as f:
        response = requests.post(
            f"{API_URL}/upload?pipeline_type=system_stability_pipeline",
            files={"file": f},
            headers=HEADERS
        )
    
    if response.status_code != 200:
        print(f"Failed to upload: {response.text}")
        return

    data = response.json()
    pipeline_id = data.get("pipeline_id")
    print(f"Upload success! Pipeline ID: {pipeline_id}")

    # 3. Poll pipeline status
    print("Polling pipeline status...")
    while True:
        res = requests.get(f"{API_URL}/pipelines/{pipeline_id}", headers=HEADERS)
        if res.status_code != 200:
            print("Failed to get pipeline status")
            break
        
        p_data = res.json()
        status = p_data.get("pipeline", {}).get("status")
        print(f"Pipeline status: {status}")
        
        if status in ["completed", "failed"]:
            print("--- Final Task List ---")
            for t in p_data.get("tasks", []):
                print(f"Task ID: {t['id']} | Type: {t['type']} | Status: {t['status']} | Worker: {t.get('assigned_worker_id')} | Duration: {t.get('execution_duration')}")
            
            print("--- Final Event Log ---")
            res_events = requests.get(f"{API_URL}/pipelines/{pipeline_id}/events", headers=HEADERS)
            if res_events.status_code == 200:
                for e in res_events.json():
                    print(f"[{e['timestamp']}] Task {e['task_id']} | Event: {e['event_type']} | Message: {e['message']} | Worker: {e.get('worker_id')}")
            
            break
        time.sleep(2)
    
    # 4. Run Retrieval Query
    print("\nRunning Retrieval Query...")
    payload = {
        "pipeline_id": pipeline_id,
        "query": "What are we testing?"
    }
    res_q = requests.post(f"{API_URL}/pipelines/retrieval", json=payload, headers=HEADERS)
    if res_q.status_code != 200:
        print(f"Failed to create query pipeline: {res_q.text}")
        return
        
    query_pid = res_q.json().get("pipeline_id")
    print(f"Query Pipeline ID: {query_pid}")
    
    while True:
        res_a = requests.get(f"{API_URL}/pipelines/retrieval/{query_pid}/answer", headers=HEADERS)
        if res_a.status_code == 200:
            ans_data = res_a.json()
            if ans_data.get("status") in ["completed", "failed"]:
                print(f"Query completed: {ans_data.get('final_answer')}")
                break
        time.sleep(1)

if __name__ == "__main__":
    run_test()
