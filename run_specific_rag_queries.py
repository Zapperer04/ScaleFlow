import requests
import time
import json
import os

# Try to load env variables first
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))
try:
    import config
    API_URL = os.getenv("API_URL", "http://127.0.0.1:5000")
    API_KEY = os.getenv("API_KEY", "dev_secret_api_key")
except ImportError:
    API_URL = os.getenv("API_URL", "http://127.0.0.1:5000")
    API_KEY = os.getenv("API_KEY", "dev_secret_api_key")

HEADERS = {"X-API-Key": API_KEY}
pipeline_id = 302  # Ingestion Pipeline ID for the large document

queries = [
    "What is this document about?",
    "Who are the main characters?",
    "Summarize chapter 1.",
    "What happens later in the document?",
    "Explain a topic that appears near the end."
]

def wait_for_pipeline(pipeline_id, timeout=120):
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

print(f"=== RUNNING 5 SPECIFIC QUERIES AGAINST PIPELINE {pipeline_id} ===")

results = []

for q in queries:
    print(f"\nSubmitting query: '{q}'...")
    payload = {
        "name": f"Spec Query: {q[:30]}",
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
        print(f"      Preview: {repr(c_text[:150])}...")
        
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
with open("specific_query_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("\nSpecific queries validation results saved to specific_query_results.json")
