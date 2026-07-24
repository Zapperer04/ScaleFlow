#!/usr/bin/env python3
"""
MR-RAG v1.0 Client Example: Retrieve Context Chunks
"""
import sys
import requests

API_URL = "http://localhost:5000/query-pipelines"
API_KEY = "local_only_secret_key"
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

def retrieve_context(query):
    print(f"Retrieving context for query: '{query}'")
    payload = {
        "query": query,
        "top_k": 5
    }
    r = requests.post(API_URL, json=payload, headers=HEADERS)
    if r.status_code != 201:
        print(f"Error: {r.status_code} {r.text}")
        sys.exit(1)
        
    data = r.json()
    pipeline_id = data["pipeline_id"]
    print(f"Pipeline #{pipeline_id} created. Fetching retrieved results...")
    
    # Retrieve raw pipeline info
    time_limit = 10
    while time_limit > 0:
        res = requests.get(f"{API_URL}/{pipeline_id}/answer", headers=HEADERS)
        if res.status_code == 200:
            status = res.json().get("status")
            if status == "completed":
                ctx = res.json().get("retrieved_context") or {}
                results = ctx.get("results", [])
                print(f"Retrieved {len(results)} chunks:")
                for idx, item in enumerate(results):
                    print(f"\n[{idx+1}] Score: {item.get('score')} | Chunk: {item.get('chunk_id')}")
                    print(f"Text snippet: {item.get('chunk_text', '')[:120]}...")
                break
        import time
        time.sleep(1)
        time_limit -= 1

if __name__ == "__main__":
    q = "What is the application number?" if len(sys.argv) < 2 else sys.argv[1]
    retrieve_context(q)
