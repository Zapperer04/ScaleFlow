import requests, json

BASE = "http://localhost:5000"
HEADERS = {"X-API-Key": "dev_secret_api_key"}

for pid in [133, 134]:
    r = requests.get(f"{BASE}/pipelines/{pid}", headers=HEADERS)
    if r.status_code == 200:
        data = r.json()
        print(f"\n================ PIPELINE {pid} ==================")
        tasks = data.get("tasks", [])
        for t in tasks:
            if t.get('type') == 'retrieve_context':
                print(f"Task {t.get('id')} ({t.get('type')}): result keys = {list(t.get('result', {}).keys())}")
                # Print individual chunk keys and details
                chunks = t.get('result', {}).get('chunks', [])
                print(f"Number of chunks: {len(chunks)}")
                for idx, c in enumerate(chunks):
                    # print snippet
                    chunk_text = c.get("chunk_text") or c.get("text") or ""
                    print(f"  Chunk {idx}: text (len={len(chunk_text)}) = {repr(chunk_text[:120])}...")
            elif t.get('type') == 'generate_answer_report':
                print(f"Task {t.get('id')} ({t.get('type')}): result keys = {list(t.get('result', {}).keys())}")
                print(f"  Answer: {t.get('result', {}).get('answer')}")
