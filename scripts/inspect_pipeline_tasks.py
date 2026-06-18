import requests, json

BASE = "http://localhost:5000"
HEADERS = {"X-API-Key": "dev_secret_api_key"}

for pid in [133, 134]:
    r = requests.get(f"{BASE}/pipelines/{pid}", headers=HEADERS)
    if r.status_code == 200:
        data = r.json()
        print(f"\n================ PIPELINE {pid} ==================")
        print("Query:", data.get("pipeline", {}).get("query"))
        # print all tasks in order
        tasks = data.get("tasks", [])
        for t in tasks:
            print(f"Task {t.get('id')} ({t.get('type')}): status={t.get('status')}")
            # If this is the RAG or LLM generation, or retrieval task
            if t.get('type') == 'retrieve_chunks':
                print("Retrieval outputs keys:", t.get('result', {}).keys())
                chunks = t.get('result', {}).get('chunks', [])
                print(f"Number of retrieved chunks: {len(chunks)}")
                for idx, c in enumerate(chunks[:3]):
                    print(f"  Chunk {idx} (score={c.get('score')}): text_len={len(c.get('chunk_text', ''))}")
            elif t.get('type') == 'generate_answer_report':
                print("Answer output:", t.get('result', {}).get('answer'))
