import time
import requests
import os
from requests.exceptions import ConnectionError, Timeout

API_URL = "http://localhost:5000"
FILE_PATH = "backend/test_data/category_A_simple.pdf"

API_KEY = "local_only_secret_key"
HEADERS = {"X-API-Key": API_KEY}

def get_with_retry(url, headers, retries=5, delay=3):
    for attempt in range(retries):
        try:
            return requests.get(url, headers=headers, timeout=10)
        except (ConnectionError, Timeout) as e:
            if attempt < retries - 1:
                print(f"  [RETRY] GET failed ({e}). Retry {attempt+1}/{retries-1} in {delay}s...")
                time.sleep(delay)
            else:
                raise

def run_test():
    print(f"Uploading {FILE_PATH}...")
    try:
        with open(FILE_PATH, "rb") as f:
            res = requests.post(f"{API_URL}/files/upload", files={"file": f}, data={"priority": "high"}, headers=HEADERS, timeout=30)
    except (ConnectionError, Timeout) as e:
        print(f"Upload failed: {e}")
        return False

    print(f"Status Code: {res.status_code}")
    if res.status_code not in [200, 201, 202]:
        print(f"Failed to upload: {res.text}")
        return False

    pipeline = res.json()
    pipeline_id = pipeline.get("pipeline_id")
    print(f"Started pipeline #{pipeline_id}")

    last_status = None
    last_tasks = {}
    timeout_at = time.time() + 300  # 5 minute max per run

    while time.time() < timeout_at:
        try:
            res = get_with_retry(f"{API_URL}/pipelines/{pipeline_id}", HEADERS)
            if res.status_code != 200:
                print(f"Failed to get pipeline: {res.text}")
                time.sleep(2)
                continue
        except Exception as e:
            print(f"Pipeline poll error: {e}")
            time.sleep(3)
            continue

        data = res.json()
        status = data.get("pipeline", {}).get("status")
        tasks = data.get("tasks", [])

        if status != last_status:
            print(f"Pipeline Status changed: {status}")
            last_status = status

        for task in tasks:
            task_id = task.get("id")
            t_status = task.get("status")
            if task_id not in last_tasks or last_tasks[task_id] != t_status:
                print(f"Task #{task_id} ({task.get('type')}) changed: {t_status}")
                print(f"  Worker: {task.get('assigned_worker_id')}")
                if task.get('error_message'):
                    print(f"  Error: {task.get('error_message')}")
                last_tasks[task_id] = t_status

        if status in ["completed", "failed"]:
            break

        time.sleep(2)
    else:
        print(f"TIMEOUT: Pipeline #{pipeline_id} did not complete in 300s")
        return False

    return status == "completed"

if __name__ == "__main__":
    successes = 0
    failures = 0
    for i in range(1, 11):
        print(f"--- RUN {i}/10 ---")
        if run_test():
            successes += 1
            print(f"Run {i} Passed")
        else:
            failures += 1
            print(f"Run {i} Failed")

    print(f"\nTest Suite Completed: {successes} Passed, {failures} Failed")
