import requests
import time
import sys

API_URL = 'http://localhost:5000'
HEADERS = {'X-API-Key': 'dev_secret_api_key'}

pipeline_id = 114

print(f'Waiting for processing of pipeline {pipeline_id}...')
for i in range(60):
    time.sleep(2)
    res = requests.get(f'{API_URL}/pipelines/{pipeline_id}', headers=HEADERS)
    pipe_data = res.json()
    status = pipe_data.get('status')
    print(f'Status: {status}')
    if status in ['completed', 'failed']:
        break

if status == 'completed':
    print("Pipeline completed! Now running queries...")
    
    questions = [
        "What skills does the candidate have?",
        "What internships has the candidate completed?",
        "What projects are listed?"
    ]

    for idx, q in enumerate(questions):
        print(f"\n==========================================")
        print(f"Question {idx+1}: {q}")
        print(f"==========================================")
        
        # We pass pipeline_id_filter to query specifically this document's pipeline
        r = requests.post(f"{API_URL}/query-pipelines", json={"query": q, "top_k": 5, "pipeline_id_filter": pipeline_id}, headers=HEADERS)
        if r.status_code != 201:
            print(f"ERROR: {r.status_code} {r.text}")
            continue
            
        qid = r.json()["pipeline_id"]
        print(f"Query pipeline #{qid} created. Polling...")
        
        for attempt in range(30):
            time.sleep(2)
            try:
                r2 = requests.get(f"{API_URL}/query-pipelines/{qid}/answer", headers=HEADERS, timeout=10)
                if r2.status_code == 200:
                    ans = r2.json()
                    q_status = ans.get("status")
                    if q_status == "completed":
                        print("Answer:", ans.get("answer"))
                        print("Sources:", ans.get("sources"))
                        break
                    elif q_status == "failed":
                        print("Query pipeline failed!")
                        break
            except Exception as e:
                print(f"Error polling: {e}")
else:
    print("Pipeline failed or timed out.")
