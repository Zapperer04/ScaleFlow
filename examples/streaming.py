#!/usr/bin/env python3
"""
MR-RAG v1.0 Client Example: Stream Answer Generation Tokens
"""
import sys
import json
import requests

API_URL = "http://localhost:5000"
API_KEY = "local_only_secret_key"
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

def stream_answer(query):
    print(f"Streaming query answer for: '{query}'")
    
    # 1. Create pipeline with streaming enabled
    payload = {
        "query": query,
        "top_k": 5,
        "stream": True
    }
    
    try:
        r = requests.post(f"{API_URL}/query-pipelines", json=payload, headers=HEADERS)
        if r.status_code != 201:
            print(f"Error: {r.status_code} {r.text}")
            sys.exit(1)
            
        pipeline_id = r.json()["pipeline_id"]
        print(f"Pipeline created: #{pipeline_id}. Listening to SSE token stream...")
        
        # 2. Connect to streaming SSE endpoint
        # Use stream=True in requests to iterate line by line
        url = f"{API_URL}/query-pipelines/{pipeline_id}/stream"
        res = requests.get(url, headers=HEADERS, stream=True)
        
        print("\n=== STREAMING RESPONSE ===")
        for line in res.iter_lines():
            if line:
                decoded_line = line.decode('utf-8').strip()
                if decoded_line.startswith("data:"):
                    data_str = decoded_line[5:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        token = data.get("token", "")
                        print(token, end="", flush=True)
                    except json.JSONDecodeError:
                        pass
        print("\n\nStream Finished.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    q = "Summarize the candidate's core expertise." if len(sys.argv) < 2 else sys.argv[1]
    stream_answer(q)
