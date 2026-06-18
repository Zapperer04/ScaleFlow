import requests
import sys
import time

API_URL = "http://localhost:5000/api/documents"
HEADERS = {'X-API-Key': 'dev_secret_api_key'}

def upload_and_monitor(file_path):
    print(f"\n--- Uploading {file_path} ---")
    with open(file_path, 'rb') as f:
        files = {'file': f}
        res = requests.post(f"{API_URL}/upload", files=files, headers=HEADERS)
        if res.status_code != 201:
            print("Upload failed:", res.text)
            return
            
    data = res.json()
    pipeline_id = data.get("pipeline_id")
    print(f"Uploaded successfully. Pipeline ID: {pipeline_id}")
    
    while True:
        res = requests.get(f"{API_URL}/pipelines/{pipeline_id}", headers=HEADERS)
        status = res.json().get("status")
        if status in ["completed", "failed"]:
            break
        time.sleep(2)
        
    res = requests.get(f"{API_URL}/pipelines/{pipeline_id}/timeline", headers=HEADERS)
    timeline = res.json()
    
    print(f"\nPipeline {pipeline_id} Timeline:")
    print(f"{'Task Type':<25} | {'Status':<10} | {'Duration (s)':<12} | {'Worker':<10}")
    print("-" * 65)
    for t in timeline:
        worker = t.get('assigned_worker_id') or '-'
        duration = t.get('execution_duration', 0)
        print(f"{t.get('task_type'):<25} | {t.get('status'):<10} | {duration:<12.2f} | {worker:<10}")

if __name__ == "__main__":
    upload_and_monitor("d:/Projects/task-schedular/backend/storage/uploads/216_ML_Notes.pdf")
    upload_and_monitor("d:/Projects/task-schedular/backend/storage/uploads/9_category_D_scanned.pdf")
