#!/usr/bin/env python3
"""
MR-RAG v1.0 Client Example: Chat Query & Answer Polling
"""
import sys
import time
import requests

API_URL = "http://localhost:5000"
API_KEY = "local_only_secret_key"
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

def run_chat_query(query):
    # 1. Submit query pipeline
    print(f"Submitting query: '{query}'")
    r = requests.post(f"{API_URL}/query-pipelines", json={"query": query, "top_k": 5}, headers=HEADERS)
    if r.status_code != 201:
        print(f"Error creating query pipeline: {r.status_code} {r.text}")
        sys.exit(1)
        
    pipeline_id = r.json()["pipeline_id"]
    print(f"Query pipeline created: #{pipeline_id}")
    
    # 2. Poll for answer status
    print("Polling for answer...")
    for i in range(20):
        time.sleep(2)
        r2 = requests.get(f"{API_URL}/query-pipelines/{pipeline_id}/answer", headers=HEADERS)
        if r2.status_code == 200:
            ans = r2.json()
            status = ans.get("status")
            print(f"  Status: {status}")
            if status == "completed":
                print("\n=== ANSWER ===")
                final = ans.get("final_answer") or {}
                print("Answer:", final.get("answer"))
                print("Confidence:", final.get("confidence"))
                print("Citations:")
                for cite in final.get("citations", []):
                    print(f"  - Chunk: {cite.get('chunk_id')} (Source: {cite.get('source_uri')})")
                sys.exit(0)
            elif status == "failed":
                print("Pipeline execution failed.")
                sys.exit(1)
        else:
            print(f"HTTP Error: {r2.status_code}")
            
    print("Timeout waiting for response.")

if __name__ == "__main__":
    q = "What projects has this candidate completed?" if len(sys.argv) < 2 else sys.argv[1]
    run_chat_query(q)
