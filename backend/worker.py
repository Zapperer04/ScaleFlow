import time
import requests
import redis
import json
import os
import random
import threading
import traceback
import re
from datetime import datetime

def load_env():
    try:
        with open('.env') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, val = line.strip().split('=', 1)
                    os.environ.setdefault(key.strip(), val.strip())
    except FileNotFoundError:
        pass

load_env()

API_URL = os.getenv("API_URL", "http://localhost:5000")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
WORKER_ID = os.getenv("WORKER_ID", "worker-1")
API_KEY = os.getenv("API_KEY", "dev_secret_api_key")

HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

print(f"[{WORKER_ID}] Initializing Redis client: host={REDIS_HOST}, port={REDIS_PORT}", flush=True)
redis_client = redis.Redis(
    host=REDIS_HOST, 
    port=REDIS_PORT, 
    decode_responses=True,
    socket_timeout=5,
    socket_connect_timeout=5
)

# Standard list of queue names
PRIORITY_QUEUES = ['task_queue_high', 'task_queue_medium', 'task_queue_low']

worker_state = {
    'status': 'idle',
    'current_task_id': None,
    'tasks_completed': 0,
    'tasks_failed': 0,
    'last_action': 'Initializing worker'
}

def send_heartbeat():
    """Send heartbeat to API every 10 seconds"""
    while True:
        try:
            payload = {
                'worker_id': WORKER_ID,
                'status': worker_state['status'],
                'current_task_id': worker_state['current_task_id'],
                'tasks_completed': worker_state['tasks_completed'],
                'tasks_failed': worker_state['tasks_failed'],
                'last_action': worker_state['last_action']
            }
            res = requests.post(f"{API_URL}/workers/heartbeat", 
                        json=payload, headers=HEADERS, timeout=5)
            if res.status_code != 200:
                print(f"[{WORKER_ID}] Heartbeat status error: {res.status_code} - {res.text}", flush=True)
        except Exception as e:
            print(f"[{WORKER_ID}] Heartbeat connection failed: {e}", flush=True)
        time.sleep(10)

try:
    from task_registry import TASK_REGISTRY
except ImportError:
    TASK_REGISTRY = {}

def handle_send_email(payload):
    print(f"[{WORKER_ID}]   -> Sending email to {payload.get('to')}", flush=True)
    if payload.get('cc'):
        print(f"[{WORKER_ID}]   -> CC: {payload.get('cc')}", flush=True)
    time.sleep(2)
    print(f"[{WORKER_ID}]   [OK] Email sent!", flush=True)

def handle_process_video(payload):
    print(f"[{WORKER_ID}]   -> Processing video {payload.get('file')}", flush=True)
    if payload.get('format'):
        print(f"[{WORKER_ID}]   -> Format: {payload.get('format')}", flush=True)
    if payload.get('resolution'):
        print(f"[{WORKER_ID}]   -> Resolution: {payload.get('resolution')}", flush=True)
    time.sleep(3)
    print(f"[{WORKER_ID}]   [OK] Video processed!", flush=True)

def handle_generate_report(payload):
    print(f"[{WORKER_ID}]   -> Generating report: {payload.get('report_type')}", flush=True)
    if payload.get('format'):
        print(f"[{WORKER_ID}]   -> Format: {payload.get('format')}", flush=True)
    time.sleep(4)
    print(f"[{WORKER_ID}]   [OK] Report generated!", flush=True)

def handle_data_backup(payload):
    print(f"[{WORKER_ID}]   -> Backing up {payload.get('database')}", flush=True)
    time.sleep(5)
    print(f"[{WORKER_ID}]   [OK] Backup completed!", flush=True)

def handle_image_processing(payload):
    print(f"[{WORKER_ID}]   -> Processing image: {payload.get('image_path')}", flush=True)
    time.sleep(3)
    print(f"[{WORKER_ID}]   [OK] Image processed!", flush=True)

def handle_send_notification(payload):
    print(f"[{WORKER_ID}]   -> Sending notification to {payload.get('user_id')}", flush=True)
    time.sleep(1)
    print(f"[{WORKER_ID}]   [OK] Notification sent!", flush=True)

def handle_run_ml_model(payload):
    print(f"[{WORKER_ID}]   -> Running ML model: {payload.get('model_name')}", flush=True)
    time.sleep(6)
    print(f"[{WORKER_ID}]   [OK] Model executed!", flush=True)

def handle_webhook_trigger(payload):
    print(f"[{WORKER_ID}]   -> Triggering webhook: {payload.get('url')}", flush=True)
    time.sleep(2)
    print(f"[{WORKER_ID}]   [OK] Webhook triggered!", flush=True)

# Phase 2 Demo Handlers
def parse_pdf_text(content):
    matches = re.findall(r'\(([^)]*)\)', content)
    if matches:
        cleaned = []
        for m in matches:
            m = m.replace(r'\(', '(').replace(r'\)', ')')
            if m.strip():
                cleaned.append(m)
        return " ".join(cleaned)
    clean_text = "".join(c for c in content if c.isprintable() or c in "\r\n\t")
    return clean_text

def handle_parse_document(payload, input_artifacts):
    text = payload.get('source_text')
    if not text and input_artifacts:
        uploaded_file_data = input_artifacts.get("uploaded_file")
        if uploaded_file_data is not None:
            if isinstance(uploaded_file_data, str) and (uploaded_file_data.startswith("%PDF") or "%PDF" in uploaded_file_data[:1024]):
                text = parse_pdf_text(uploaded_file_data)
            else:
                text = str(uploaded_file_data)
        else:
            text = list(input_artifacts.values())[0]
            if isinstance(text, dict) and "content" in text:
                text = text["content"]
    if not text:
        text = ""
    normalized = text.strip()
    print(f"[{WORKER_ID}]   [OK] Parsed document of length {len(normalized)}", flush=True)
    return normalized

def handle_chunk_text(payload, input_artifacts):
    text = input_artifacts.get("parsed_text", "")
    if not text:
        text = payload.get("source_text", "")
        
    chunks = []
    words = text.split()
    current_chunk = []
    current_len = 0
    for word in words:
        current_chunk.append(word)
        current_len += len(word) + 1
        if current_len >= 300:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_len = 0
    if current_chunk:
        chunks.append(" ".join(current_chunk))
        
    if not chunks:
        chunks = [text]
        
    print(f"[{WORKER_ID}]   [OK] Chunked text into {len(chunks)} chunks", flush=True)
    return chunks

def get_pipeline_file_info(pipeline_id):
    file_id = None
    original_filename = None
    uploaded_art_id = None
    
    # 1. Fetch pipeline details (which has artifacts)
    try:
        res = requests.get(f"{API_URL}/pipelines/{pipeline_id}", headers=HEADERS, timeout=5)
        if res.status_code == 200:
            p_data = res.json()
            artifacts = p_data.get("artifacts", [])
            for art in artifacts:
                if art.get("artifact_type") == "uploaded_file":
                    uploaded_art_id = art.get("id")
                    meta = art.get("metadata_json") or art.get("metadata") or {}
                    if isinstance(meta, str):
                        try:
                            meta = json.loads(meta)
                        except:
                            meta = {}
                    original_filename = meta.get("original_filename")
    except Exception as e:
        print(f"[{WORKER_ID}] Error fetching pipeline detail: {e}", flush=True)

    # 2. Fetch files list to find the matching file_id
    try:
        res_files = requests.get(f"{API_URL}/files", headers=HEADERS, timeout=5)
        if res_files.status_code == 200:
            files_list = res_files.json()
            for f in files_list:
                if f.get("pipeline_id") == pipeline_id:
                    file_id = f.get("id")
                    if not original_filename:
                        original_filename = f.get("original_filename")
                    break
    except Exception as e:
        print(f"[{WORKER_ID}] Error fetching files list: {e}", flush=True)
        
    return file_id, original_filename, uploaded_art_id

def get_artifact_content_by_type(pipeline_id, artifact_type):
    from context.artifact_store import load_artifact_from_disk
    try:
        res = requests.get(f"{API_URL}/pipelines/{pipeline_id}", headers=HEADERS, timeout=5)
        if res.status_code == 200:
            data = res.json()
            for art in data.get("artifacts", []):
                if art.get("artifact_type") == artifact_type:
                    storage_uri = art.get("storage_uri")
                    return load_artifact_from_disk(storage_uri)
    except Exception as e:
        print(f"[{WORKER_ID}] Error fetching artifact {artifact_type} for pipeline {pipeline_id}: {e}", flush=True)
    return None

def handle_generate_embeddings(payload, input_artifacts):
    from services.embedding_service import embed_chunks
    from services.vector_store import upsert_document_chunks
    
    # Read text_chunks or error_patterns
    chunks = input_artifacts.get("text_chunks") or input_artifacts.get("error_patterns") or []
    if isinstance(chunks, str):
        chunks = [chunks]
    elif isinstance(chunks, dict):
        chunks = [json.dumps(chunks)]
        
    pipeline_id = payload.get('_pipeline_id')
    task_id = payload.get('_task_id')
    
    print(f"[{WORKER_ID}]   -> Generating real embeddings for {len(chunks)} chunks in pipeline {pipeline_id}...", flush=True)
    
    # Generate real embeddings (384-dimensional)
    vectors = []
    if chunks:
        try:
            vectors = embed_chunks(chunks)
        except Exception as e:
            print(f"[{WORKER_ID}] Embedding failed: {e}. Using deterministic fallback.", flush=True)
            from services.embedding_service import deterministic_fallback_embed
            vectors = [deterministic_fallback_embed(chunk) for chunk in chunks]
        
    # Get context details via helper
    file_id = None
    original_filename = None
    source_artifact_id = None
    if pipeline_id:
        file_id, original_filename, source_artifact_id = get_pipeline_file_info(pipeline_id)
        
    # Upsert to Qdrant
    qdrant_upserted = False
    if chunks and vectors:
        meta_dict = {
            "source_artifact_id": source_artifact_id,
            "original_filename": original_filename
        }
        qdrant_upserted = upsert_document_chunks(
            pipeline_id=pipeline_id,
            file_id=file_id,
            task_id=task_id,
            chunks=chunks,
            vectors=vectors,
            metadata=meta_dict
        )
        
    # Build the chunk refs for the artifact
    chunk_refs = []
    for idx, chunk in enumerate(chunks):
        chunk_refs.append({
            "chunk_index": idx,
            "chunk_text": chunk[:100] + "..." if len(chunk) > 100 else chunk
        })
        
    # Create vector_index artifact data
    artifact_data = {
        "collection": "scaleflow_chunks",
        "vector_count": len(chunks),
        "embedding_model": "all-MiniLM-L6-v2",
        "dimension": 384,
        "qdrant_upserted": qdrant_upserted,
        "chunk_refs": chunk_refs
    }
    
    print(f"[{WORKER_ID}]   [OK] Generated vector index with {len(chunks)} points (upserted to Qdrant: {qdrant_upserted})", flush=True)
    return artifact_data

def handle_summarize_document(payload, input_artifacts):
    pipeline_id = payload.get('_pipeline_id')
    # 1. First, check if text_chunks is directly in input_artifacts
    chunks = input_artifacts.get("text_chunks")
    if not chunks:
        # 2. Check if we have vector_index or embeddings_mock in input_artifacts
        # If we have vector_index, we can fetch text_chunks from pipeline artifacts
        if pipeline_id:
            chunks = get_artifact_content_by_type(pipeline_id, "text_chunks")
            
    if not chunks:
        # 3. Fallback to embeddings_mock or vector_index (for backward compatibility / tests)
        embeddings = input_artifacts.get("embeddings_mock") or input_artifacts.get("vector_index")
        if embeddings and isinstance(embeddings, list):
            chunks = [item.get("chunk_preview", "") for item in embeddings if isinstance(item, dict)]
        elif embeddings and isinstance(embeddings, dict) and "chunk_refs" in embeddings:
            # Maybe the vector_index stored chunk_refs
            chunks = [ref.get("chunk_text", "") for ref in embeddings.get("chunk_refs", []) if isinstance(ref, dict)]
            if not any(chunks) and pipeline_id:
                chunks = get_artifact_content_by_type(pipeline_id, "text_chunks")
        else:
            text = input_artifacts.get("parsed_text", "")
            if not text and pipeline_id:
                text = get_artifact_content_by_type(pipeline_id, "parsed_text")
            if text:
                chunks = [text]
            else:
                chunks = []
                
    if not chunks:
        chunks = ["No content to summarize."]
        
    summary_chunks = chunks[:2]
    summary = "SUMMARY:\n" + "\n".join(summary_chunks)
    print(f"[{WORKER_ID}]   [OK] Generated extractive summary", flush=True)
    return summary

def handle_parse_logs(payload, input_artifacts):
    text = payload.get("source_text", "")
    if not text and input_artifacts:
        uploaded_file_data = input_artifacts.get("uploaded_file")
        if uploaded_file_data is not None:
            text = str(uploaded_file_data)
        else:
            text = list(input_artifacts.values())[0]
            if isinstance(text, dict) and "content" in text:
                text = text["content"]
        
    lines = text.splitlines()
    parsed = [line.strip() for line in lines if line.strip()]
    print(f"[{WORKER_ID}]   [OK] Parsed {len(parsed)} log lines", flush=True)
    return parsed

def handle_detect_error_patterns(payload, input_artifacts):
    logs = input_artifacts.get("parsed_logs", [])
    errors = []
    for log in logs:
        log_upper = log.upper()
        if "ERROR" in log_upper or "WARN" in log_upper or "FAIL" in log_upper or "CRITICAL" in log_upper:
            errors.append(log)
            
    print(f"[{WORKER_ID}]   [OK] Detected {len(errors)} error patterns in logs", flush=True)
    return errors

def handle_summarize_logs(payload, input_artifacts):
    errors = input_artifacts.get("error_patterns") or input_artifacts.get("parsed_logs") or []
    summary = f"LOG ANALYSIS SUMMARY:\nTotal anomalous entries detected: {len(errors)}\n"
    if errors:
        summary += "Sample errors:\n"
        for err in errors[:5]:
            summary += f"- {err}\n"
            
    print(f"[{WORKER_ID}]   [OK] Summarized logs with {len(errors)} anomalies", flush=True)
    return summary

def handle_final_report(payload, input_artifacts):
    errors = input_artifacts.get("error_patterns", [])
    summary = input_artifacts.get("log_summary", "")
    
    report = "========================================\n"
    report += "FINAL LOG ANALYSIS PIPELINE REPORT\n"
    report += "========================================\n\n"
    report += f"Status: COMPLETED\n"
    report += f"Anomalies Count: {len(errors)}\n\n"
    report += summary
    
    print(f"[{WORKER_ID}]   [OK] Generated final report", flush=True)
    return report

HANDLER_MAP = {
    "send_email": handle_send_email,
    "process_video": handle_process_video,
    "generate_report": handle_generate_report,
    "data_backup": handle_data_backup,
    "image_processing": handle_image_processing,
    "send_notification": handle_send_notification,
    "run_ml_model": handle_run_ml_model,
    "webhook_trigger": handle_webhook_trigger,
    "parse_document": handle_parse_document,
    "chunk_text": handle_chunk_text,
    "generate_embeddings": handle_generate_embeddings,
    "summarize_document": handle_summarize_document,
    "parse_logs": handle_parse_logs,
    "detect_error_patterns": handle_detect_error_patterns,
    "summarize_logs": handle_summarize_logs,
    "final_report": handle_final_report
}

OUTPUT_ARTIFACT_TYPES = {
    "parse_document": "parsed_text",
    "chunk_text": "text_chunks",
    "generate_embeddings": "vector_index",
    "summarize_document": "summary",
    "parse_logs": "parsed_logs",
    "detect_error_patterns": "error_patterns",
    "summarize_logs": "log_summary",
    "final_report": "final_report"
}

def execute_task(task):
    """Simulate doing the actual work - with random failures for testing retry"""
    from context.artifact_store import load_artifact_from_disk, save_artifact_to_disk
    task_type = task['type']
    task_data = task['data']
    task_id = task['id']
    retry_count = task.get('retry_count', 0)
    priority = task.get('priority', 'medium')
    
    print(f"[{WORKER_ID}] [{datetime.now().strftime('%H:%M:%S')}] Executing task {task_id}: {task_type} [Priority: {priority.upper()}] (Attempt {retry_count + 1})", flush=True)
    
    # Check for simulate_hang_seconds in payload
    simulate_hang_seconds = task_data.get('simulate_hang_seconds')
    if simulate_hang_seconds is not None:
        try:
            hang_time = float(simulate_hang_seconds)
            print(f"[{WORKER_ID}]   [HANG] [Simulation] Hanging task for {hang_time} seconds...", flush=True)
            time.sleep(hang_time)
            print(f"[{WORKER_ID}]   [HANG] [Simulation] Wake up after hang!", flush=True)
        except (ValueError, TypeError):
            print(f"[{WORKER_ID}]   [WARN] Invalid simulate_hang_seconds value: {simulate_hang_seconds}", flush=True)

    if random.random() < 0.1 and retry_count < 2:
        print(f"[{WORKER_ID}]   [FAIL] Task failed! Will retry...", flush=True)
        raise Exception(f"Simulated failure for task {task_id}")
    
    # Check in handler map
    handler = HANDLER_MAP.get(task_type)
    if not handler:
        registry_info = TASK_REGISTRY.get(task_type, {})
        handler_name = registry_info.get("handler_name")
        if handler_name:
            handler = globals().get(handler_name)
            
    if handler:
        if task_type in OUTPUT_ARTIFACT_TYPES:
            # Load input artifacts
            input_artifacts = {}
            for art_id in task.get('input_artifact_ids', []):
                try:
                    res_art = requests.get(f"{API_URL}/artifacts/{art_id}", headers=HEADERS, timeout=5)
                    if res_art.status_code == 200:
                        meta = res_art.json()
                        art_type = meta.get('artifact_type')
                        storage_uri = meta.get('storage_uri')
                        data = load_artifact_from_disk(storage_uri)
                        input_artifacts[art_type] = data
                except Exception as ex:
                    print(f"[{WORKER_ID}] Error loading input artifact {art_id}: {ex}", flush=True)
            
            # Execute handler
            if isinstance(task_data, dict):
                task_data['_task_id'] = task_id
                task_data['_pipeline_id'] = task.get('pipeline_id')
            output_data = handler(task_data, input_artifacts)
            
            # Save artifact to disk
            pipeline_id = task.get('pipeline_id')
            artifact_type = OUTPUT_ARTIFACT_TYPES[task_type]
            storage_uri, checksum = save_artifact_to_disk(pipeline_id, task_id, artifact_type, output_data)
            
            # Register artifact with API
            res_reg = requests.post(
                f"{API_URL}/artifacts",
                json={
                    "pipeline_id": pipeline_id,
                    "task_id": task_id,
                    "artifact_type": artifact_type,
                    "storage_uri": storage_uri,
                    "checksum": checksum,
                    "metadata": {"worker_id": WORKER_ID}
                },
                headers=HEADERS,
                timeout=5
            )
            if res_reg.status_code != 201:
                raise Exception(f"Failed to register output artifact: {res_reg.status_code} - {res_reg.text}")
                
            created_artifact = res_reg.json()
            task['output_artifact_ids'] = [created_artifact['id']]
        else:
            handler(task_data)
    else:
        print(f"[{WORKER_ID}]   [WARN] Unknown task type / handler: {task_type}", flush=True)

def get_next_task():
    """Get next task from highest priority queue that has tasks"""
    try:
        result = redis_client.brpop(PRIORITY_QUEUES, timeout=5)
        if result:
            return result
    except redis.exceptions.ConnectionError as ce:
        print(f"[{WORKER_ID}] Redis connection error during brpop: {ce}", flush=True)
        raise ce
    except redis.exceptions.TimeoutError:
        pass
    except Exception as e:
        print(f"[{WORKER_ID}] Error in get_next_task: {e}", flush=True)
        traceback.print_exc()
    return None

def worker_loop():
    worker_state['last_action'] = 'Verifying Redis'
    print(f"[{WORKER_ID}] Worker started! Verifying Redis connection...", flush=True)
    try:
        redis_client.ping()
        print(f"[{WORKER_ID}] Connected to Redis successfully!", flush=True)
    except Exception as e:
        print(f"[{WORKER_ID}] CRITICAL: Failed to connect to Redis: {e}", flush=True)
    
    print(f"[{WORKER_ID}] PRIORITY_QUEUES type: {type(PRIORITY_QUEUES)}, value: {PRIORITY_QUEUES}", flush=True)
    print(f"[{WORKER_ID}] Listening on queue names: {PRIORITY_QUEUES}", flush=True)
    print(f"[{WORKER_ID}] Heartbeat enabled - sending to {API_URL}/workers/heartbeat every 10s", flush=True)
    
    heartbeat_thread = threading.Thread(target=send_heartbeat, daemon=True)
    heartbeat_thread.start()
    
    while True:
        try:
            worker_state['last_action'] = 'Waiting for task'
            print(f"[{WORKER_ID}] Waiting for task...", flush=True)
            result = get_next_task()
            
            if result:
                queue_name, task_id = result
                task_id = task_id.decode() if isinstance(task_id, bytes) else str(task_id)
                worker_state['last_action'] = f"Received task #{task_id}"
                print(f"[{WORKER_ID}] Received task_id {task_id} from queue {queue_name}", flush=True)
                
                worker_state['last_action'] = f"Claiming task #{task_id}"
                print(f"[{WORKER_ID}] Claiming task #{task_id} from API...", flush=True)
                response = requests.post(f"{API_URL}/tasks/{task_id}/claim", json={'worker_id': WORKER_ID}, headers=HEADERS, timeout=5)
                
                if response.status_code != 200:
                    worker_state['last_action'] = f"Failed to claim task #{task_id}"
                    print(f"[{WORKER_ID}] Claim failed: {response.status_code} - {response.text}", flush=True)
                    continue
                    
                task = response.json()
                lease_token = task.get('lease_token')
                
                worker_state['last_action'] = f"Executing task #{task_id}"
                print(f"[{WORKER_ID}] Starting task {task_id} ({task.get('type')})...", flush=True)
                worker_state['status'] = 'busy'
                worker_state['current_task_id'] = task_id
                
                try:
                    retry_count = task.get('retry_count', 0)
                    if retry_count > 0:
                        delay = min(2 ** retry_count, 30)
                        worker_state['last_action'] = f"Backing off task #{task_id} for {delay}s"
                        print(f"[{WORKER_ID}] Waiting {delay}s backoff before retry...", flush=True)
                        time.sleep(delay)
                        worker_state['last_action'] = f"Executing task #{task_id}"
                    
                    execute_task(task)
                    
                    output_artifact_ids = task.get('output_artifact_ids', [])
                    res_complete = requests.patch(f"{API_URL}/tasks/{task_id}", 
                                 json={
                                     'status': 'completed', 
                                     'worker_id': WORKER_ID, 
                                     'lease_token': lease_token,
                                     'output_artifact_ids': output_artifact_ids
                                 }, headers=HEADERS, timeout=5)
                    if res_complete.status_code != 200:
                        print(f"[{WORKER_ID}] Warning: failed to patch status to completed: {res_complete.status_code} - {res_complete.text}", flush=True)
                        if res_complete.status_code == 409:
                            print(f"[{WORKER_ID}] [WARN] Task completion rejected: lease expired or owned by another worker.", flush=True)
                    else:
                        worker_state['tasks_completed'] += 1
                        
                    worker_state['last_action'] = f"Completed task #{task_id}"
                    print(f"[{WORKER_ID}] Completed task {task_id} successfully!", flush=True)
                    
                except Exception as e:
                    worker_state['last_action'] = f"Failed task #{task_id}"
                    print(f"[{WORKER_ID}] Failed task {task_id}: {str(e)}", flush=True)
                    res_fail = requests.patch(f"{API_URL}/tasks/{task_id}", 
                                 json={
                                     'status': 'failed',
                                     'error_message': str(e),
                                     'worker_id': WORKER_ID,
                                     'lease_token': lease_token
                                 }, headers=HEADERS, timeout=5)
                    if res_fail.status_code != 200:
                        print(f"[{WORKER_ID}] Warning: failed to patch status to failed: {res_fail.status_code} - {res_fail.text}", flush=True)
                        if res_fail.status_code == 409:
                            print(f"[{WORKER_ID}] [WARN] Task failure report rejected: lease expired or owned by another worker.", flush=True)
                    else:
                        worker_state['tasks_failed'] += 1
                    
                finally:
                    worker_state['status'] = 'idle'
                    worker_state['current_task_id'] = None
            else:
                pass
                
        except Exception as e:
            worker_state['last_action'] = f"Loop Exception: {str(e)[:20]}"
            print(f"[{WORKER_ID}] Loop Exception: {e}", flush=True)
            traceback.print_exc()
            time.sleep(2)

if __name__ == "__main__":
    print("WORKER MAIN STARTED", flush=True)
    worker_loop()