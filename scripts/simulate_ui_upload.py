import requests
import json
import time
import os

API_URL = "http://localhost:5000"
FILE_PATH = "backend/storage/uploads/6_category_A_simple.pdf"
HEADERS = {"X-API-Key": "dev_secret_api_key"}

print(f"Uploading {FILE_PATH}...")
with open(FILE_PATH, 'rb') as f:
    res = requests.post(
        f"{API_URL}/files/upload",
        files={"file": f},
        data={"priority": "high", "pipeline_type": "document_processing_demo"},
        headers=HEADERS
    )

if res.status_code != 201:
    print(f"Upload failed: {res.status_code}")
    print(res.text)
    exit(1)

pipeline_id = res.json().get('pipeline_id')
print(f"Pipeline created: #{pipeline_id}")

last_pipeline_status = None
task_states = {}

print("\n--- BEGINNING TRACE ---")

while True:
    time.sleep(1)
    p_res = requests.get(f"{API_URL}/pipelines/{pipeline_id}", headers=HEADERS)
    if p_res.status_code != 200:
        continue
    
    data = p_res.json()
    pipeline = data['pipeline']
    tasks = data.get('tasks', [])
    
    # Check pipeline status changes
    if pipeline['status'] != last_pipeline_status:
        print(f"[PIPELINE #{pipeline_id}] Status transitioned to: {pipeline['status']}")
        print(f"  --> Orchestrator Owner: {pipeline.get('owner_instance_id')}")
        last_pipeline_status = pipeline['status']
        
    for t in tasks:
        tid = t['id']
        current_status = t['status']
        if tid not in task_states:
            task_states[tid] = {'status': None}
            
        if current_status != task_states[tid]['status']:
            worker = t.get('assigned_worker_id')
            error = t.get('error_message')
            lease_token = t.get('lease_token')
            print(f"[TASK #{tid}] {t['type']} transitioned to: {current_status}")
            print(f"  --> Assigned Worker: {worker}")
            print(f"  --> Lease Token: {lease_token}")
            if error:
                print(f"  --> Error: {error}")
            task_states[tid]['status'] = current_status
            
    if pipeline['status'] in ['completed', 'failed']:
        print(f"\n--- TRACE COMPLETE ---")
        print(f"Final Pipeline Status: {pipeline['status']}")
        break
