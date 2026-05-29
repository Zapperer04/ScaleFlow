import requests
import time
import json
import os

API_URL = "http://localhost:5000"
HEADERS = {"X-API-Key": "dev_secret_api_key"}
pipeline_id = 293  # Pipeline ID for The Billion Dollar Sure Thing

queries = [
    "What is this book about?",
    "Who are the main characters?",
    "Summarize the opening section."
]

def wait_for_pipeline(pipeline_id, timeout=300):
    start = time.time()
    while time.time() - start < timeout:
        res = requests.get(f"{API_URL}/pipelines/{pipeline_id}", headers=HEADERS)
        if res.status_code == 200:
            data = res.json()
            status = data.get("pipeline", {}).get("status")
            if status in ('completed', 'failed', 'cancelled'):
                return data
        time.sleep(1)
    raise TimeoutError(f"Pipeline {pipeline_id} timed out")

print(f"=== RETRIEVAL DEEP VALIDATION FOR PIPELINE {pipeline_id} ===")

results = []

for q in queries:
    print(f"\nSubmitting query: '{q}'...")
    payload = {
        "name": f"Validation Query: {q[:30]}",
        "pipeline_type": "retrieval_answer_demo",
        "initial_payload": {
            "query": q,
            "target_pipeline_id": pipeline_id,
            "pipeline_id_filter": pipeline_id
        }
    }
    
    start_time = time.time()
    res = requests.post(f"{API_URL}/pipelines", json=payload, headers=HEADERS)
    if res.status_code != 201:
        print(f"Error submitting query: {res.text}")
        continue
        
    q_pid = res.json().get('pipeline_id')
    print(f"Query Pipeline ID: {q_pid}. Polling for answer...")
    
    data = wait_for_pipeline(q_pid)
    total_duration = round(time.time() - start_time, 2)
    
    # Latency Breakdown from tasks
    embed_time = 0.0
    search_time = 0.0
    generation_time = 0.0
    
    for task in data.get("tasks", []):
        t_type = task.get("type")
        duration = task.get("execution_duration") or 0.0
        if t_type == "embed_query":
            embed_time = round(duration, 3)
        elif t_type == "retrieve_context":
            search_time = round(duration, 3)
        elif t_type == "generate_answer_report":
            generation_time = round(duration, 3)
            
    # Retrieve top chunks from retrieved_context artifact
    retrieved_chunks = []
    for art in data.get('artifacts', []):
        if art.get('artifact_type') == 'retrieved_context':
            meta = art.get('metadata_json')
            if isinstance(meta, str):
                meta = json.loads(meta)
            retrieved_chunks = meta.get('results', [])
            break
            
    # Also fetch the final answer
    final_answer_text = ""
    for art in data.get('artifacts', []):
        if art.get('artifact_type') == 'final_answer':
            meta = art.get('metadata_json')
            if isinstance(meta, str):
                meta = json.loads(meta)
            final_answer_text = meta.get('answer', "")
            break
            
    print(f"Query Pipeline {q_pid} completed in {total_duration}s.")
    print(f"  - Embedding Latency: {embed_time}s")
    print(f"  - Search Latency: {search_time}s")
    print(f"  - Generation Latency: {generation_time}s")
    
    print(f"Top Chunks retrieved (count={len(retrieved_chunks)}):")
    for i, c in enumerate(retrieved_chunks[:5]):
        c_text = c.get('chunk_text', c.get('text', ''))
        c_id = c.get('chunk_index', c.get('chunk_id', 'N/A'))
        print(f"  [{i+1}] Chunk ID: {c_id}")
        print(f"      Score: {c.get('score')}")
        print(f"      Preview: {repr(c_text[:300])}...")
        
    results.append({
        "query": q,
        "pipeline_id": q_pid,
        "total_duration": total_duration,
        "embed_time": embed_time,
        "search_time": search_time,
        "generation_time": generation_time,
        "chunks": retrieved_chunks,
        "answer": final_answer_text
    })

# Save results JSON
with open("deep_validation_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("\nDeep validation results saved to deep_validation_results.json")
