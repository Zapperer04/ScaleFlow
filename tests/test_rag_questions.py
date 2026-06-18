import requests
import time
import sys

BASE = "http://localhost:5000"
HEADERS = {"X-API-Key": "dev_secret_api_key", "Content-Type": "application/json"}

questions = [
    "What skills does the candidate have?",
    "What internships has the candidate completed?",
    "What projects are listed?"
]

for idx, q in enumerate(questions):
    print(f"\n==========================================")
    print(f"Question {idx+1}: {q}")
    print(f"==========================================")
    
    r = requests.post(f"{BASE}/query-pipelines", json={"query": q, "top_k": 5}, headers=HEADERS)
    if r.status_code != 201:
        print(f"ERROR: {r.status_code} {r.text}")
        continue
        
    pipeline_id = r.json()["pipeline_id"]
    print(f"Pipeline #{pipeline_id} created. Polling...")
    
    for attempt in range(30):
        time.sleep(2)
        try:
            r2 = requests.get(f"{BASE}/query-pipelines/{pipeline_id}/answer", headers=HEADERS, timeout=10)
            if r2.status_code == 200:
                ans = r2.json()
                status = ans.get("status")
                if status == "completed":
                    print("Answer:", ans.get("answer"))
                    print("Sources:", ans.get("sources"))
                    break
                elif status == "failed":
                    print("Pipeline failed!")
                    break
        except Exception as e:
            print(f"Error polling: {e}")
            
