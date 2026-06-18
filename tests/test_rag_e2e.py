import requests
import time
import sys

BASE = "http://localhost:5000"
HEADERS = {"X-API-Key": "dev_secret_api_key", "Content-Type": "application/json"}

query = "what projects has this candidate built"

# 1. Submit query pipeline
print(f"[1] Submitting query: '{query}'")
r = requests.post(f"{BASE}/query-pipelines", json={"query": query, "top_k": 5}, headers=HEADERS)
if r.status_code != 201:
    print(f"ERROR creating query pipeline: {r.status_code} {r.text}")
    sys.exit(1)

data = r.json()
pipeline_id = data["pipeline_id"]
print(f"[1] Query pipeline created: #{pipeline_id}")

# 2. Poll for answer (max 120 seconds)
print(f"[2] Polling for answer on pipeline #{pipeline_id}...")
for i in range(40):
    time.sleep(3)
    try:
        # Use a fresh session each poll to avoid Waitress keep-alive drops on Windows
        with requests.Session() as s:
            r2 = s.get(f"{BASE}/query-pipelines/{pipeline_id}/answer", headers=HEADERS, timeout=15)
    except Exception as e:
        print(f"  [{i*3}s] Connection error (retry): {e}")
        continue
    if r2.status_code == 200:
        ans = r2.json()
        # Endpoint returns 'status', not 'pipeline_status'
        status = ans.get("status")
        print(f"  [{i*3}s] Pipeline status: {status}")
        if status == "completed":
            print("\n=== RAG ANSWER ===")
            final = ans.get("final_answer") or {}
            print("Answer:", final.get("answer", "N/A"))
            print("Confidence:", final.get("confidence", "N/A"))
            ctx = ans.get("retrieved_context") or {}
            chunks = ctx.get("results", [])
            print(f"Chunks retrieved: {len(chunks)}")
            for c in chunks[:3]:
                print(f"  Score={c.get('score','?')} Text={str(c.get('chunk_text',''))[:80]}")
            sys.exit(0)
        elif status in ("failed",):
            print(f"  Pipeline failed!")
            print("Full response:", ans)
            sys.exit(1)
    else:
        print(f"  [{i*3}s] HTTP {r2.status_code}: {r2.text[:200]}")

print("TIMEOUT: Pipeline did not complete in 120 seconds")
