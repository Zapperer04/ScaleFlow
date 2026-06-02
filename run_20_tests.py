import os
import time
import requests
import json
import datetime

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
TOTAL_RUNS = int(os.getenv("TOTAL_RUNS", "20"))

def wait_for_backend():
    print("Waiting for backend to become healthy...")
    for _ in range(300): # 10 minutes max
        try:
            res = requests.get(f"{API_URL}/task-types")
            if res.status_code == 200:
                print("Backend is healthy!")
                return True
        except Exception:
            pass
        time.sleep(2)
    return False

def get_task_duration(tasks, task_type):
    for t in tasks:
        if t['type'] == task_type:
            return t.get('execution_duration', 'N/A')
    return 'N/A'

def run_single_pipeline(run_idx):
    print(f"\n========================================\nRUN #{run_idx}\n========================================")
    
    # 1. Create a simple txt file
    with open("test_document.txt", "w") as f:
        f.write(f"This is test run {run_idx} for deterministic execution reliability.\nWe must prove stability before moving forward. Adding more text to satisfy the minimum chunk size requirement of the semantic chunker which filters out short texts under forty words. This document now contains enough words to be successfully chunked, embedded, and indexed into our Qdrant vector database.")

    # 2. Upload the file
    upload_start = time.time()
    with open("test_document.txt", "rb") as f:
        response = requests.post(
            f"{API_URL}/files/upload",
            data={"pipeline_type": "system_stability_pipeline"},
            files={"file": f},
            headers=HEADERS
        )
    
    if response.status_code not in (200, 201):
        print(f"FAILED AT UPLOAD: {response.text}")
        return False, "Upload failed"

    data = response.json()
    pipeline_id = data.get("pipeline_id")
    enqueue_time = datetime.datetime.now().isoformat()
    print(f"Upload success! Pipeline ID: {pipeline_id}")

    # 3. Poll pipeline status
    max_wait = 120 # 2 minutes max per pipeline
    start_wait = time.time()
    final_status = "unknown"
    p_data = None
    
    while time.time() - start_wait < max_wait:
        res = requests.get(f"{API_URL}/pipelines/{pipeline_id}", headers=HEADERS)
        if res.status_code != 200:
            print("FAILED AT STATUS POLL")
            return False, "Status poll failed"
        
        p_data = res.json()
        status = p_data.get("pipeline", {}).get("status")
        
        if status in ["completed", "failed", "cancelled"]:
            final_status = status
            break
        time.sleep(2)
        
    if final_status != "completed":
        print(f"PIPELINE FAILED OR TIMED OUT. Final status: {final_status}")
        print(json.dumps(p_data, indent=2))
        return False, "Pipeline execution failed or stalled"
    if not p_data:
        return False, "p_data is None"
        
    tasks = p_data.get("tasks", [])
    
    parse_dur = get_task_duration(tasks, 'parse_document')
    chunk_dur = get_task_duration(tasks, 'chunk_text')
    embed_dur = get_task_duration(tasks, 'generate_embeddings')
    
    # Check if Qdrant insertion succeeded (we injected it in generate_embeddings trace or artifact)
    vector_index_art = next((a for a in p_data.get("artifacts", []) if a.get("artifact_type") == "vector_index"), None)
    if not vector_index_art or not vector_index_art.get("metadata_json", {}).get("qdrant_upserted"):
        print("FAILED AT QDRANT INSERTION")
        return False, "Qdrant insertion failed"
    qdrant_dur = "Included in embed" # because it's in the same task

    # Identify worker assignment
    worker_assigned = "N/A"
    for t in tasks:
        if t.get('assigned_worker_id'):
            worker_assigned = t['assigned_worker_id']
            break

    # 4. Run Retrieval Query
    retrieval_start = time.time()
    payload = {
        "pipeline_id_filter": pipeline_id,
        "query": "What are we testing?"
    }
    res_q = requests.post(f"{API_URL}/query-pipelines", json=payload, headers=HEADERS)
    if res_q.status_code not in (200, 201):
        print(f"FAILED AT QUERY CREATION: {res_q.text}")
        return False, "Query creation failed"
        
    query_pid = res_q.json().get("pipeline_id")
    
    q_status = "unknown"
    while time.time() - retrieval_start < 120:
        res_a = requests.get(f"{API_URL}/query-pipelines/{query_pid}/answer", headers=HEADERS)
        if res_a.status_code == 200:
            ans_data = res_a.json()
            q_status = ans_data.get("status")
            print(f"  Query status: {q_status} ({time.time() - retrieval_start:.1f}s)", flush=True)
            if q_status in ["completed", "failed", "cancelled"]:
                break
        else:
            print(f"  Query poll failed with code: {res_a.status_code}", flush=True)
        time.sleep(2)
        
    retrieval_dur = f"{time.time() - retrieval_start:.2f}s"
    if q_status != "completed":
        print(f"FAILED AT RETRIEVAL. Status: {q_status}")
        return False, "Retrieval failed"

    # Log the summary for this run
    print(f"* pipeline_id: {pipeline_id}")
    print(f"* enqueue timestamp: {enqueue_time}")
    print(f"* worker assignment: {worker_assigned}")
    print(f"* parse duration: {parse_dur}")
    print(f"* chunk duration: {chunk_dur}")
    print(f"* embedding duration: {embed_dur}")
    print(f"* qdrant insertion duration: {qdrant_dur}")
    print(f"* retrieval duration: {retrieval_dur}")
    print(f"* final status: {final_status}")
    
    # Save trace log
    res_events = requests.get(f"{API_URL}/events/pipelines/{pipeline_id}", headers=HEADERS)
    if res_events.status_code == 200:
        events = res_events.json()
        with open(f"trace_run_{run_idx}.log", "w") as f:
            for e in events:
                f.write(f"[{e.get('created_at', 'N/A')}] Task {e.get('task_id', 'N/A')} | Event: {e.get('event_type', 'N/A')} | Message: {e.get('message', 'N/A')} | Worker: {e.get('worker_id', 'N/A')}\n")
    
    return True, "Success"

def run_all_tests():
    if not wait_for_backend():
        print("Backend not available. Aborting.")
        return

    for i in range(1, TOTAL_RUNS + 1):
        success, reason = run_single_pipeline(i)
        if not success:
            print(f"\n>>> TEST FAILED ON RUN {i}. REASON: {reason} <<<")
            print("Stopping test suite immediately.")
            return
            
        time.sleep(2) # brief pause between runs

    print(f"\n========================================\nALL {TOTAL_RUNS} RUNS COMPLETED SUCCESSFULLY!\n========================================")

if __name__ == "__main__":
    run_all_tests()
