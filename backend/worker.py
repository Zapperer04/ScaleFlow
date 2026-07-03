import time
import requests
import redis
from redis.exceptions import ConnectionError as RedisConnectionError, TimeoutError as RedisTimeoutError
from typing import Any
import json
import os
import random
import threading
import traceback
import re
from datetime import datetime

def load_env():
    for path in ['.env', 'backend/.env', '../backend/.env', '../../.env']:
        try:
            with open(path) as f:
                for line in f:
                    if line.strip() and not line.startswith('#'):
                        key, val = line.strip().split('=', 1)
                        key_strip = key.strip()
                        if key_strip not in os.environ:
                            os.environ[key_strip] = val.strip()
                break
        except FileNotFoundError:
            pass

load_env()

import config

API_URL = os.getenv("API_URL", "http://127.0.0.1:5000")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
WORKER_ID = os.getenv("WORKER_ID", "worker-1")
API_KEY = os.getenv("API_KEY", "dev_secret_api_key")

HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

# Self-healing API_URL detection inside Docker
if "host.docker.internal" in API_URL:
    try:
        requests.get(f"{API_URL}/task-types", timeout=1.0)
    except Exception as e_host:
        print(f"[{WORKER_ID}] [Self-Healing] Connection to {API_URL} failed ({e_host}). Probing fallbacks...", flush=True)
        fallbacks = ["http://backend:5000", "http://172.17.0.1:5000", "http://172.18.0.1:5000", "http://10.0.75.1:5000"]
        for test_url in fallbacks:
            try:
                res = requests.get(f"{test_url}/task-types", timeout=1.0)
                if res.status_code == 200:
                    print(f"[{WORKER_ID}] [Self-Healing] Successfully resolved API_URL to: {test_url}", flush=True)
                    API_URL = test_url
                    break
            except Exception:
                pass

print(f"[{WORKER_ID}] Initializing Redis client: host={REDIS_HOST}, port={REDIS_PORT}", flush=True)
redis_client = redis.Redis(
    host=REDIS_HOST, 
    port=REDIS_PORT, 
    decode_responses=True,
    socket_timeout=5,
    socket_connect_timeout=5
)

WORKER_CAPABILITIES_STR = os.getenv("WORKER_CAPABILITIES", "default,cpu_heavy,embedding_gpu,summarization_llm,retrieval_optimized,io_heavy")
try:
    WORKER_CAPABILITIES = json.loads(WORKER_CAPABILITIES_STR)
    if not isinstance(WORKER_CAPABILITIES, list):
        WORKER_CAPABILITIES = [WORKER_CAPABILITIES_STR]
except Exception:
    WORKER_CAPABILITIES = [c.strip() for c in WORKER_CAPABILITIES_STR.split(",") if c.strip()]

ALL_WORKER_QUEUES = []
for p in ['high', 'medium', 'low']:
    for cap in WORKER_CAPABILITIES:
        ALL_WORKER_QUEUES.append(f"task_queue_test_{cap}_{p}")
        ALL_WORKER_QUEUES.append(f"task_queue_{cap}_{p}")

worker_state: dict[str, Any] = {
    'status': 'idle',
    'current_task_id': None,
    'tasks_completed': 0,
    'tasks_failed': 0,
    'last_action': 'Initializing worker'
}

def send_heartbeat():
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

def emit_task_trace(task_id, message):
    if not task_id:
        return
    try:
        payload = {
            "worker_id": WORKER_ID,
            "event_type": "task_trace",
            "message": message
        }
        requests.post(f"{API_URL}/tasks/{task_id}/log", json=payload, headers=HEADERS, timeout=5)
    except Exception as e:
        print(f"[{WORKER_ID}] Failed to emit task trace: {e}", flush=True)

try:
    from task_registry import TASK_REGISTRY, LEASE_DURATIONS
except ImportError:
    TASK_REGISTRY = {}
    LEASE_DURATIONS = {}

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

def get_uploaded_file_path(pipeline_id):
    try:
        res = requests.get(f"{API_URL}/pipelines/{pipeline_id}", headers=HEADERS, timeout=5)
        if res.status_code == 200:
            data = res.json()
            for art in data.get("artifacts", []):
                if art.get("artifact_type") == "uploaded_file":
                    storage_uri = art.get("storage_uri")
                    from context.artifact_store import BASE_STORAGE_DIR
                    normalized = storage_uri.replace("\\", "/")
                    if "storage/" in normalized:
                        rel_path = normalized.split("storage/", 1)[1]
                    else:
                        rel_path = os.path.basename(normalized)
                    full_path = os.path.normpath(os.path.join(BASE_STORAGE_DIR, rel_path))
                    return full_path
    except Exception as e:
        print(f"[{WORKER_ID}] Error fetching uploaded file path: {e}", flush=True)
    return None

# ─────────────────────────────────────────────────────────────────────────────
# Document Preprocessing
# ─────────────────────────────────────────────────────────────────────────────
def handle_preprocess_document(payload, input_artifacts):
    pipeline_id = payload.get('_pipeline_id')
    task_id     = payload.get('_task_id')

    def _trace(msg: str):
        print(f"[{WORKER_ID}] {msg}", flush=True)
        emit_task_trace(task_id, msg)

    _trace("[PREPROCESS] Preprocessing stage started")

    filepath = get_uploaded_file_path(pipeline_id)
    if not filepath or not os.path.exists(filepath):
        raise FileNotFoundError(f"[PREPROCESS] Uploaded file not found. Resolved path: {filepath!r}")

    from services.document_preprocessor import evaluate_document, run_enhancement_pipeline
    import dataclasses
    
    report = evaluate_document(filepath, trace_fn=_trace)
    
    if report.needs_enhancement:
        _worker_dir = os.path.dirname(os.path.abspath(__file__))
        _temp_dir   = os.path.join(_worker_dir, "storage", "temp")
        import pypdf
        with open(filepath, "rb") as f:
            _pc = len(pypdf.PdfReader(f).pages)
        enhanced_dir = run_enhancement_pipeline(
            filepath=filepath,
            report=report,
            pipeline_id=str(pipeline_id),
            output_dir=_temp_dir,
            page_count=_pc
        )
        if enhanced_dir:
            report.used_enhancement = True
            report.enhanced_pages_path = enhanced_dir
            _trace(f"[PREPROCESS] Enhancement complete: saved to {os.path.basename(enhanced_dir)}")
            
    report_dict = dataclasses.asdict(report)
    return report_dict


def handle_parse_document(payload, input_artifacts):
    """Parse document into a document graph (VLM-first) or plain text (legacy)."""
    pipeline_id = payload.get('_pipeline_id')
    task_id = payload.get('_task_id')
    lease_token = payload.get('_lease_token')
    progress_json = payload.get('_progress_json')

    def _trace(msg: str):
        print(f"[{WORKER_ID}] {msg}", flush=True)
        emit_task_trace(task_id, msg)

    filepath = get_uploaded_file_path(pipeline_id)
    if not filepath or not os.path.exists(filepath):
        raise FileNotFoundError(f"[PARSER] Uploaded file not found. Resolved path: {filepath!r}")

    file_id, original_filename, _ = get_pipeline_file_info(pipeline_id)
    is_pdf = original_filename.lower().endswith(".pdf") if original_filename else filepath.lower().endswith(".pdf")

    if is_pdf:
        _trace("[PARSER] PDF detected — starting VLM-first parser")
        try:
            prep = input_artifacts.get("preprocessing_report", {})
            document_type = prep.get("document_type", "MULTIMODAL")
            routing_confidence = prep.get("routing_confidence", 1.0)
            parse_method_hint = prep.get("parse_method_hint", "vlm_document_graph")
            enhanced_pages_path = prep.get("enhanced_pages_path")

            from services.pdf_parser import parse_pdf
            result = parse_pdf(
                filepath=filepath,
                task_id=task_id,
                lease_token=lease_token,
                progress_json=progress_json if isinstance(progress_json, dict) else {},
                trace_fn=_trace,
                api_url=API_URL,
                api_headers=HEADERS,
                skip_ocr=False,
                document_type=document_type,
                routing_confidence=routing_confidence,
                parse_method_hint=parse_method_hint,
                enhanced_pages_path=enhanced_pages_path
            )
            # result is a ParseResult with document_graph, stats, pages
            document_graph = result.document_graph
            parse_stats = result.stats
            pages = result.pages
            _trace(f"[PARSER] VLM parsing complete. Nodes: {parse_stats.get('node_count', 0)}, edges: {parse_stats.get('edge_count', 0)}")
            # Return a dict compatible with downstream graph-native chunker
            return {
                "document_graph": document_graph,
                "parse_stats": parse_stats,
                "pages": pages,
                "document_type": document_type,
                "routing_confidence": routing_confidence
            }
        except ValueError as ve:
            _trace(f"[PARSER] VALIDATION FAILURE: {ve}")
            raise
        except TimeoutError as te:
            _trace(f"[PARSER] TIMEOUT: {te}")
            raise Exception(str(te))
        except Exception as e:
            _trace(f"[PARSER] CRITICAL ERROR: {e}")
            raise
    else:
        # Plain text / log file – fallback to reading as plain text
        _trace("[PARSER] Plain-text file detected — reading directly")
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            _trace(f"[PARSER] Read {len(text)} chars from file")
            # For plain text, we wrap in a minimal document graph (single node)
            document_graph = {
                "document_id": str(task_id),
                "parser": "plaintext",
                "pages": [{
                    "page_number": 1,
                    "nodes": [{
                        "chunk_id": "p1_n1",
                        "type": "paragraph",
                        "text": text,
                        "section": "unknown",
                        "reading_order": 1,
                        "bbox": {"x1": 0, "y1": 0, "x2": 1, "y2": 1}
                    }],
                    "edges": []
                }]
            }
            return {
                "document_graph": document_graph,
                "parse_stats": {"parser": "plaintext"},
                "pages": [{"page_number": 1, "extraction_method": "raw_text"}],
                "document_type": "TEXT",
                "routing_confidence": 1.0
            }
        except Exception as e:
            _trace(f"[PARSER] ERROR reading file: {e}")
            raise

    # Fallback (should not reach)
    return {
        "document_graph": {},
        "parse_stats": {},
        "pages": [],
        "document_type": "UNKNOWN",
        "routing_confidence": 0.0
    }


def handle_validate_parse_quality(payload, input_artifacts):
    """Quality Gate verifying the parsed document text before chunking."""
    task_id = payload.get('_task_id')
    pipeline_id = payload.get('_pipeline_id')
    
    def _trace(msg: str):
        print(f"[{WORKER_ID}] {msg}", flush=True)
        emit_task_trace(task_id, msg)
        
    _trace("[QUALITY GATE] Starting parse quality validation gate...")
    
    raw_input = input_artifacts.get("parsed_text", {})
    text = ""
    parse_stats = {}
    document_graph = raw_input.get("document_graph") if isinstance(raw_input, dict) else None
    # For quality gate, we extract text from the graph for analysis (if available)
    if document_graph:
        # Concatenate all node texts for quality scoring
        all_texts = []
        for page in document_graph.get("pages", []):
            for node in page.get("nodes", []):
                all_texts.append(node.get("text", ""))
        text = "\n".join(all_texts)
        parse_stats = raw_input.get("parse_stats", {})
    else:
        if isinstance(raw_input, dict):
            text = raw_input.get("parsed_text", "")
            parse_stats = raw_input.get("parse_stats", {})
        else:
            text = raw_input or payload.get("source_text", "")
    
    if not text:
        _trace("[QUALITY GATE] FAILED: No text was extracted from the document.")
        raise ValueError("Document unreadable / OCR quality too low: Extracted text is empty.")

    preprocess_report = input_artifacts.get("preprocessing_report", {})
    document_type = preprocess_report.get("document_type", "SCANNED")
    extractable_text_ratio = preprocess_report.get("extractable_text_ratio", 0.0)

    from services.quality_gate_service import validate_quality
    try:
        metrics = validate_quality(text, parse_stats, document_type, extractable_text_ratio)
        # Pass through the document graph and other fields unchanged
        if isinstance(raw_input, dict):
            if "document_graph" in raw_input:
                metrics["document_graph"] = raw_input["document_graph"]
            if "pages" in raw_input:
                metrics["pages"] = raw_input["pages"]
            if "document_type" in raw_input:
                metrics["document_type"] = raw_input["document_type"]
            if "routing_confidence" in raw_input:
                metrics["routing_confidence"] = raw_input["routing_confidence"]
        
        _trace(f"[QUALITY GATE] Ingestion Parser Used: {metrics['parser_used'].upper()}")
        _trace(f"[QUALITY GATE] PASSED: Document parsing quality is within acceptable bounds.")
        return metrics
    except ValueError as ve:
        _trace(f"[QUALITY GATE] FAILED: {str(ve)}")
        raise ve


# ─────────────────────────────────────────────────────────────────────────────
# Graph‑native Semantic Chunker
# ─────────────────────────────────────────────────────────────────────────────
def handle_chunk_text(payload, input_artifacts):
    """
    Graph‑native chunking: uses document graph if available, else falls back to text chunking.
    """
    task_id = payload.get('_task_id')
    raw_input = input_artifacts.get("parsed_text", {})
    document_graph = raw_input.get("document_graph") if isinstance(raw_input, dict) else None

    if document_graph:
        _trace_msg = "[CHUNKER] Graph‑native chunking started"
        emit_task_trace(task_id, _trace_msg)
        print(f"[{WORKER_ID}] {_trace_msg}", flush=True)
        from services.chunking_service import chunk_document_graph
        t_start = time.perf_counter()
        result = chunk_document_graph(document_graph)
        chunks = result["chunks"]  # list of dicts with 'text', 'metadata', etc.
        duration = time.perf_counter() - t_start
        emit_task_trace(task_id, f"[CHUNKER] Generated {len(chunks)} graph chunks (took {duration:.4f}s)")
        print(f"[{WORKER_ID}]   [OK] Graph-chunked into {len(chunks)} chunks", flush=True)
        return chunks
    else:
        # Legacy plain text chunking
        text = raw_input.get("parsed_text", "") if isinstance(raw_input, dict) else str(raw_input)
        if not text:
            text = payload.get("source_text", "")
        emit_task_trace(task_id, "[CHUNKER] Legacy text chunking started")
        from services.chunking_service import chunk_text
        pages = raw_input.get("pages", []) if isinstance(raw_input, dict) else []
        if not pages:
            pages = [{"page_number": 1, "text": text}]
        output_chunks = []
        active_section = "unknown"
        active_parent = None
        for page in pages:
            page_text = page.get("text", "")
            if not page_text.strip():
                continue
            page_chunks = chunk_text(
                page_text,
                page_number=page.get("page_number", 0),
                default_section=active_section,
                default_parent=active_parent
            )
            if hasattr(page_chunks, 'active_section'):
                active_section = page_chunks.active_section
            if hasattr(page_chunks, 'active_parent'):
                active_parent = page_chunks.active_parent
            for seg in page_chunks:
                if isinstance(seg, dict):
                    seg_text = seg.get('text', '')
                    seg_meta = seg.get('metadata', {})
                else:
                    seg_text = str(seg)
                    seg_meta = {}
                output_chunks.append({
                    "text": seg_text,
                    "metadata": seg_meta
                })
        print(f"[{WORKER_ID}]   [OK] Text-chunked into {len(output_chunks)} chunks", flush=True)
        return output_chunks

def get_pipeline_file_info(pipeline_id):
    file_id = None
    original_filename = None
    uploaded_art_id = None
    
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
                # FIXED: use the function argument, not the literal string
                if art.get("artifact_type") == artifact_type:
                    storage_uri = art.get("storage_uri")
                    return load_artifact_from_disk(storage_uri)
    except Exception as e:
        print(f"[{WORKER_ID}] Error fetching artifact {artifact_type} for pipeline {pipeline_id}: {e}", flush=True)
    return None

def handle_generate_embeddings(payload, input_artifacts):
    from services.embedding_service import embed_chunks_with_progress, get_model_load_time
    from services.vector_store import upsert_document_chunks

    task_id     = payload.get('_task_id')
    pipeline_id = payload.get('_pipeline_id')
    MAX_EMBED_CHUNKS = config.MAX_CHUNKS

    def _trace(msg: str):
        print(f"[{WORKER_ID}] {msg}", flush=True)
        emit_task_trace(task_id, msg)

    raw = input_artifacts.get("text_chunks") or []
    
    # Graph chunks are list of dicts with 'text' and possibly 'metadata'
    if isinstance(raw, list) and raw and isinstance(raw[0], dict) and "text" in raw[0]:
        # Graph-native chunks: use as is
        chunks = [item["text"] for item in raw]
        chunk_metadata = [item.get("metadata", {}) for item in raw]
    elif isinstance(raw, str):
        chunks = [raw]
        chunk_metadata = [{}]
    elif isinstance(raw, dict):
        if "text" in raw and "metadata" in raw:
            chunks = [raw["text"]]
            chunk_metadata = [raw["metadata"]]
        else:
            chunks = [json.dumps(raw)]
            chunk_metadata = [{}]
    elif isinstance(raw, list):
        # Mixed list
        chunks = []
        chunk_metadata = []
        for item in raw:
            if isinstance(item, dict) and "text" in item:
                chunks.append(item["text"])
                chunk_metadata.append(item.get("metadata", {}))
            elif isinstance(item, str):
                chunks.append(item)
                chunk_metadata.append({})
            elif isinstance(item, dict):
                chunks.append(json.dumps(item))
                chunk_metadata.append({})
            else:
                chunks.append(str(item))
                chunk_metadata.append({})
    else:
        chunks = []
        chunk_metadata = []

    if len(chunks) > MAX_EMBED_CHUNKS:
        _trace(f"[EMBED] WARNING: {len(chunks)} chunks exceeds limit {MAX_EMBED_CHUNKS}. Truncating.")
        chunks = chunks[:MAX_EMBED_CHUNKS]
        chunk_metadata = chunk_metadata[:MAX_EMBED_CHUNKS]

    _trace(f"[EMBED] Generating embeddings for {len(chunks)} chunks (model: {config.EMBEDDING_MODEL}, dim={config.EMBEDDING_DIMENSION})")

    # Prepare embedding texts using the new embedding service (which now handles dicts natively)
    embedded_chunks_data = []
    for i, chunk_text in enumerate(chunks):
        meta = chunk_metadata[i] if i < len(chunk_metadata) else {}
        if isinstance(raw, list) and raw and isinstance(raw[0], dict) and "text" in raw[0]:
            embedded_chunks_data.append(raw[i])  # pass full dict
        else:
            # Legacy string
            embedded_chunks_data.append(chunk_text)

    qdrant_upserted = False
    qdrant_lookup_duration = 0.0
    qdrant_insertion_duration = 0.0
    embed_generation_duration = 0.0
    model_load_duration = 0.0

    file_id, original_filename, source_artifact_id = get_pipeline_file_info(pipeline_id) if pipeline_id else (None, None, None)

    UPSERT_BATCH_SIZE = 128
    total_chunks = len(chunks)

    if chunks:
        from services.embedding_service import get_embedding_model
        get_embedding_model()
        model_load_duration = get_model_load_time()

        t_embed_start = time.perf_counter()
        
        for i in range(0, total_chunks, UPSERT_BATCH_SIZE):
            batch_data = embedded_chunks_data[i:i + UPSERT_BATCH_SIZE]
            batch_texts = chunks[i:i + UPSERT_BATCH_SIZE]
            batch_meta = chunk_metadata[i:i + UPSERT_BATCH_SIZE]

            def _batch_trace(batch_num, total_batches, done, total):
                pass
            batch_vectors = embed_chunks_with_progress(
                batch_data, 
                progress_callback=_batch_trace, 
                batch_size=config.EMBEDDING_BATCH_SIZE
            )

            meta_dict = {
                "global_metadata": {
                    "source_artifact_id": source_artifact_id,
                    "original_filename": original_filename
                },
                "chunk_metadata": batch_meta
            }
            batch_indices = list(range(i, i + len(batch_texts)))
            # Unified collection
            batch_upserted, lookup_dur, insert_dur = upsert_document_chunks(
                pipeline_id=pipeline_id,
                file_id=file_id,
                task_id=task_id,
                chunks=batch_texts,   # still pass plain text for legacy compatibility
                vectors=batch_vectors,
                metadata=meta_dict,
                collection_name=config.QDRANT_COLLECTION_NAME,
                chunk_indices=batch_indices
            )
            qdrant_upserted = qdrant_upserted or batch_upserted
            qdrant_lookup_duration += lookup_dur
            qdrant_insertion_duration += insert_dur

            # Paragraph/Tables collections remain as before
            p_indices = [idx for idx, m in enumerate(batch_meta) if m.get("content_type") != "table"]
            if p_indices:
                p_chunks = [batch_texts[idx] for idx in p_indices]
                p_vectors = [batch_vectors[idx] for idx in p_indices]
                p_meta = [batch_meta[idx] for idx in p_indices]
                meta_dict_p = {
                    "global_metadata": {"source_artifact_id": source_artifact_id, "original_filename": original_filename},
                    "chunk_metadata": p_meta
                }
                p_global_indices = [i + idx for idx in p_indices]
                upsert_document_chunks(
                    pipeline_id=pipeline_id,
                    file_id=file_id,
                    task_id=task_id,
                    chunks=p_chunks,
                    vectors=p_vectors,
                    metadata=meta_dict_p,
                    collection_name=config.QDRANT_PARAGRAPH_COLLECTION,
                    chunk_indices=p_global_indices
                )

            t_indices = [idx for idx, m in enumerate(batch_meta) if m.get("content_type") == "table"]
            if t_indices:
                t_chunks = [batch_texts[idx] for idx in t_indices]
                t_vectors = [batch_vectors[idx] for idx in t_indices]
                t_meta = [batch_meta[idx] for idx in t_indices]
                meta_dict_t = {
                    "global_metadata": {"source_artifact_id": source_artifact_id, "original_filename": original_filename},
                    "chunk_metadata": t_meta
                }
                t_global_indices = [i + idx for idx in t_indices]
                upsert_document_chunks(
                    pipeline_id=pipeline_id,
                    file_id=file_id,
                    task_id=task_id,
                    chunks=t_chunks,
                    vectors=t_vectors,
                    metadata=meta_dict_t,
                    collection_name=config.QDRANT_TABLE_COLLECTION,
                    chunk_indices=t_global_indices
                )

            _trace(f"[EMBED] Progress: {min(i + UPSERT_BATCH_SIZE, total_chunks)}/{total_chunks} chunks embedded & indexed")

        embed_generation_duration = time.perf_counter() - t_embed_start

    chunk_refs = [
        {"chunk_index": idx, "chunk_text": (c[:120] + "...") if len(c) > 120 else c}
        for idx, c in enumerate(chunks)
    ]

    artifact_data = {
        "collection": "scaleflow_chunks",
        "vector_count": len(chunks),
        "embedding_model": config.EMBEDDING_MODEL,
        "dimension": config.EMBEDDING_DIMENSION,
        "qdrant_upserted": qdrant_upserted,
        "chunk_refs": chunk_refs,
        "model_load_duration": round(model_load_duration, 5),
        "embedding_generation_duration": round(embed_generation_duration, 5),
        "batch_size_used": config.EMBEDDING_BATCH_SIZE,
        "total_chunks_embedded": len(chunks),
        "qdrant_collection_lookup_duration": round(qdrant_lookup_duration, 5),
        "qdrant_insertion_duration": round(qdrant_insertion_duration, 5)
    }

    _trace(f"[EMBED] Complete — {len(chunks)} vectors (qdrant_upserted={qdrant_upserted})")
    return artifact_data

def handle_summarize_document(payload, input_artifacts):
    pipeline_id = payload.get('_pipeline_id')
    chunks = input_artifacts.get("text_chunks")
    if not chunks:
        if pipeline_id:
            chunks = get_artifact_content_by_type(pipeline_id, "text_chunks")
    if not chunks:
        embeddings = input_artifacts.get("embeddings_mock") or input_artifacts.get("vector_index")
        if embeddings and isinstance(embeddings, list):
            chunks = [item.get("chunk_preview", "") for item in embeddings if isinstance(item, dict)]
        elif embeddings and isinstance(embeddings, dict) and "chunk_refs" in embeddings:
            chunks = [ref.get("chunk_text", "") for ref in embeddings.get("chunk_refs", []) if isinstance(ref, dict)]
            if not any(chunks) and pipeline_id:
                chunks = get_artifact_content_by_type(pipeline_id, "text_chunks")
        else:
            text = input_artifacts.get("parsed_text", "")
            if not text and pipeline_id:
                text = get_artifact_content_by_type(pipeline_id, "parsed_text")
            if isinstance(text, dict):
                text = text.get("parsed_text", "")
            if text:
                chunks = [text]
            else:
                chunks = []
    if not chunks:
        chunks = ["No content to summarize."]
        
    processed_chunks = []
    for c in chunks:
        if isinstance(c, dict) and "text" in c:
            processed_chunks.append(c["text"])
        elif isinstance(c, str):
            processed_chunks.append(c)
        elif isinstance(c, dict):
            processed_chunks.append(json.dumps(c))
        else:
            processed_chunks.append(str(c))
    summary_chunks = processed_chunks[:2]
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
    if not isinstance(text, str):
        text = str(text)
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

def to_int_or_none(val):
    if val is None or str(val).strip() == "":
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None

def handle_embed_query(payload, input_artifacts):
    from services.embedding_service import embed_text
    query = payload.get("query")
    if not query:
        raise ValueError("Missing 'query' in embed_query task payload")
    vector = embed_text(query)
    print("=" * 80, flush=True)
    print("EMBEDDING QUERY", flush=True)
    print(f"QUERY: {query}", flush=True)
    print(f"GENERATED EMBEDDING SIZE: {len(vector)}", flush=True)
    print("=" * 80, flush=True)
    artifact_data = {
        "query": query,
        "embedding_model": "BAAI/bge-base-en-v1.5",
        "dimension": 768,
        "vector": vector,
        "top_k": payload.get("top_k"),
        "pipeline_id_filter": payload.get("pipeline_id_filter") or payload.get("pipeline_id"),
        "pipeline_id": payload.get("pipeline_id_filter") or payload.get("pipeline_id"),
        "file_id_filter": payload.get("file_id_filter") or payload.get("file_id"),
        "file_id": payload.get("file_id_filter") or payload.get("file_id")
    }
    print(f"[{WORKER_ID}] [OK] Generated query vector for query: {query[:50]}...", flush=True)
    return artifact_data

def is_general_query(query: str) -> bool:
    if not query:
        return False
    q = query.lower().strip("?. ")
    general_phrases = [
        "what is it about", "what is this document about", "what is this about",
        "summarize", "summary", "give me a summary", "what does it talk about",
        "what is this", "tell me about this", "what is the document about",
        "what is the file about", "summarize this document", "summarize this file"
    ]
    for phrase in general_phrases:
        if phrase in q:
            return True
    return False

def handle_retrieve_context(payload, input_artifacts):
    query_vector_data = input_artifacts.get("query_vector")
    if not query_vector_data:
        raise ValueError("Missing 'query_vector' in retrieve_context input artifacts")
    query = query_vector_data.get("query")
    vector = query_vector_data.get("vector")
    top_k = query_vector_data.get("top_k")
    pipeline_id_filter = query_vector_data.get("pipeline_id_filter") or query_vector_data.get("pipeline_id")
    file_id_filter = query_vector_data.get("file_id_filter") or query_vector_data.get("file_id")
    p_id = pipeline_id_filter
    if p_id is not None:
        try:
            p_id = int(p_id)
        except (ValueError, TypeError):
            pass
    print("=" * 80, flush=True)
    print("RETRIEVAL TASK INITIATED", flush=True)
    print(f"QUERY: {query}", flush=True)
    print(f"PIPELINE FILTER: {p_id if p_id is not None else 'GLOBAL (all documents)'}", flush=True)
    print(f"TOP-K: {top_k}", flush=True)
    print("=" * 80, flush=True)
    from services.retrieval_service import retrieve_and_rerank
    artifact_data = retrieve_and_rerank(query_vector=vector, pipeline_id=p_id, top_k=top_k or 5, query=query)
    filtered_results = artifact_data.get("results", [])
    print(f"[{WORKER_ID}] [OK] Retrieved {len(filtered_results)} context chunks", flush=True)
    return artifact_data

# ─────────────────────────────────────────────────────────────────────────────
# BM25 Index Building Handler
# ─────────────────────────────────────────────────────────────────────────────
def handle_build_bm25_index(payload, input_artifacts):
    """
    Build a BM25 index for the pipeline using graph chunks.
    """
    from services.bm25_service import build_bm25_index

    pipeline_id = payload.get('_pipeline_id')
    task_id = payload.get('_task_id')

    def _trace(msg: str):
        print(f"[{WORKER_ID}] {msg}", flush=True)
        emit_task_trace(task_id, msg)

    # Obtain chunks from input artifacts (either 'text_chunks' or 'graph_chunks')
    chunks = input_artifacts.get("text_chunks") or input_artifacts.get("graph_chunks") or []
    if not chunks:
        raise ValueError("No graph chunks provided for BM25 indexing")

    # Ensure each chunk has a proper chunk_id and pipeline_id
    for idx, chunk in enumerate(chunks):
        if isinstance(chunk, dict):
            chunk.setdefault("pipeline_id", pipeline_id)
            # Generate unique chunk_id if missing; use index to avoid duplicates
            if "chunk_id" not in chunk:
                chunk["chunk_id"] = chunk.get("chunk_index", f"cg_{pipeline_id}_{idx}")

    result = build_bm25_index(pipeline_id=pipeline_id, chunks=chunks)
    _trace(f"[BM25] Index built: {result['documents_indexed']} documents indexed at {result['index_path']}")

    return {
        "pipeline_id": pipeline_id,
        "bm25_indexed_documents": result["documents_indexed"],
        "bm25_index_path": result["index_path"],
        "bm25_success": result["success"]
    }


# ─────────────────────────────────────────────────────────────────────────────
# Answer Synthesis
# ─────────────────────────────────────────────────────────────────────────────
def handle_generate_answer_report(payload, input_artifacts):
    context_data = input_artifacts.get("retrieved_context")
    if not context_data:
        raise ValueError("Missing 'retrieved_context' in generate_answer_report input artifacts")
    query = context_data.get("query", "")
    results: list[Any] = context_data.get("results", [])
    min_score = float(os.getenv("MIN_RETRIEVAL_SCORE", "0.3"))
    try:
        valid_results = [r for r in results if float(r.get("score") or 0.0) >= min_score or r.get("chunk_index") == -1]
    except Exception as e:
        print(f"[{WORKER_ID}] [ERROR] Filtering results failed: {e}. Results: {results}", flush=True)
        valid_results = []
    
    print("=" * 80, flush=True)
    print("TOP MATCHES (BEFORE ANSWER SYNTHESIS):", flush=True)
    for idx, hit in enumerate(valid_results):
        score = hit.get("score")
        p_id = hit.get("pipeline_id")
        text_snippet = hit.get("chunk_text") or hit.get("text") or ""
        c_id = hit.get("chunk_index") or hit.get("chunk_id") or -1
        print(f"Match {idx+1}:", flush=True)
        print(f"  Score: {score}", flush=True)
        print(f"  Pipeline ID: {p_id}", flush=True)
        print(f"  Chunk ID: {c_id}", flush=True)
        print(f"  Snippet: {text_snippet[:300]}...", flush=True)
    print("=" * 80, flush=True)

    top_chunks = valid_results[:3]
    retrieved_count = len(results) * 3  
    reranked_count = len(results)
    context_window = ""
    for idx, c in enumerate(top_chunks):
        context_window += f"[Source {idx+1}]: {c.get('chunk_text', '')}\n"
    system_prompt_len = 175
    prompt_length = len(context_window) + len(query) + system_prompt_len
    estimated_token_length = prompt_length // 4

    if not top_chunks:
        answer = "No sufficiently relevant context was found for this query."
        citations = []
        confidence = "low"
        provider_used = "Local Heuristic Synthesizer"
        response_status = "404 Empty"
    else:
        from services.llm_service import generate_answer
        answer, provider_used, response_status = generate_answer(query, top_chunks)
        fallback_phrases = [
            "sufficient information", "no sufficiently relevant context", 
            "does not contain sufficient information", "not contain sufficient"
        ]
        is_fallback = any(phrase in answer.lower() for phrase in fallback_phrases)
        if is_fallback:
            confidence = "low"
        else:
            stopwords = {
                "the", "a", "an", "and", "or", "but", "if", "then", "else", "when", "at", "by", "from", 
                "for", "with", "about", "against", "between", "into", "through", "during", "before", 
                "after", "above", "below", "to", "of", "in", "on", "he", "she", "it", "they", "we", "you", 
                "i", "is", "was", "were", "are", "be", "been", "being", "have", "has", "had", "do", "does", 
                "did", "shall", "will", "should", "would", "may", "might", "must", "can", "could", "this", 
                "that", "these", "those", "based", "on", "retrieved", "context", "document"
            }
            clean_answer = re.sub(r'^(based on the retrieved|according to the|the document states|the patent states)[^:]*:\s*', '', answer, flags=re.IGNORECASE)
            words = re.findall(r"\b[a-zA-Z0-9_-]+\b", clean_answer.lower())
            content_words = [w for w in words if w not in stopwords]
            if content_words:
                context_lower = context_window.lower()
                matches = sum(1 for w in content_words if w in context_lower)
                grounding_score = matches / len(content_words)
            else:
                grounding_score = 1.0
            top_score = valid_results[0].get("score", 0.0) if valid_results else 0.0
            if grounding_score >= 0.85:
                if top_score >= 0.65:
                    confidence = "high"
                elif top_score >= 0.50:
                    confidence = "medium"
                else:
                    confidence = "low"
            elif grounding_score >= 0.50:
                if top_score >= 0.70:
                    confidence = "medium"
                else:
                    confidence = "low"
            else:
                confidence = "low"
        citations = []
        seen_citations = set()
        for idx, hit in enumerate(top_chunks):
            fname = hit.get("original_filename") or "unknown_file"
            fid = hit.get("file_id")
            cidx = hit.get("chunk_index", 0)
            citation_key = (fid, cidx)
            if citation_key not in seen_citations:
                seen_citations.add(citation_key)
                citations.append({
                    "file_id": fid,
                    "original_filename": fname,
                    "chunk_index": cidx
                })
        
    print("=" * 80, flush=True)
    print(f"RAG ANSWER GENERATION OBSERVABILITY:", flush=True)
    print(f"  - Retrieved chunk count: {retrieved_count}", flush=True)
    print(f"  - Reranked chunk count: {reranked_count}", flush=True)
    print(f"  - Final prompt token length (est): {estimated_token_length}", flush=True)
    print(f"  - LLM provider used: {provider_used}", flush=True)
    print(f"  - Raw LLM response status: {response_status}", flush=True)
    print("=" * 80, flush=True)
        
    artifact_data = {
        "query": query,
        "answer": answer,
        "citations": citations,
        "confidence": confidence
    }
    print(f"[{WORKER_ID}] [OK] Generated final answer with {len(citations)} citations and confidence '{confidence}'", flush=True)
    return artifact_data

TASK_HANDLERS = {
    "preprocess_document": handle_preprocess_document,
    "parse_document": handle_parse_document,
    "process_video": handle_process_video,
    "generate_report": handle_generate_report,
    "data_backup": handle_data_backup,
    "image_processing": handle_image_processing,
    "send_notification": handle_send_notification,
    "run_ml_model": handle_run_ml_model,
    "webhook_trigger": handle_webhook_trigger,
    "validate_parse_quality": handle_validate_parse_quality,
    "chunk_text": handle_chunk_text,
    "generate_embeddings": handle_generate_embeddings,
    "summarize_document": handle_summarize_document,
    "parse_logs": handle_parse_logs,
    "detect_error_patterns": handle_detect_error_patterns,
    "summarize_logs": handle_summarize_logs,
    "final_report": handle_final_report,
    "embed_query": handle_embed_query,
    "retrieve_context": handle_retrieve_context,
    "generate_answer_report": handle_generate_answer_report,
    "build_bm25_index": handle_build_bm25_index
}

OUTPUT_ARTIFACT_TYPES = {
    "preprocess_document": "preprocessing_report",
    "parse_document": "parsed_text",
    "validate_parse_quality": "parsed_text",
    "chunk_text": "text_chunks",
    "generate_embeddings": "vector_index",
    "summarize_document": "summary",
    "parse_logs": "parsed_logs",
    "detect_error_patterns": "error_patterns",
    "summarize_logs": "log_summary",
    "final_report": "final_report",
    "embed_query": "query_vector",
    "retrieve_context": "retrieved_context",
    "generate_answer_report": "final_answer",
    "build_bm25_index": "bm25_index"
}

LEASE_DURATIONS = {
    "preprocess_document": 120,
    "send_email": 30,
    "process_video": 120,
    "generate_report": 60,
    "parse_document": 60,
    "validate_parse_quality": 60,
    "chunk_text": 60,
    "generate_embeddings": 600,
    "summarize_document": 60,
    "parse_logs": 60,
    "detect_error_patterns": 60,
    "summarize_logs": 60,
    "final_report": 60,
    "embed_query": 60,
    "retrieve_context": 60,
    "generate_answer_report": 60,
    "build_bm25_index": 300
}

current_renewer = None

class LeaseRenewer(threading.Thread):
    def __init__(self, task_id, task_type, lease_token):
        super().__init__(name=f"LeaseRenewer-{task_id}")
        self.task_id = task_id
        self.task_type = task_type
        self.lease_token = lease_token
        self.stop_event = threading.Event()
        self.aborted = False
        self.daemon = True

    def run(self):
        lease_duration = LEASE_DURATIONS.get(self.task_type, 30)
        interval = max(1, min(15, lease_duration // 3))
        while not self.stop_event.wait(interval):
            if self.stop_event.is_set():
                break
            try:
                payload = {
                    "worker_id": WORKER_ID,
                    "lease_token": self.lease_token,
                    "extend_by_seconds": lease_duration
                }
                res = requests.post(
                    f"{API_URL}/tasks/{self.task_id}/renew-lease", 
                    json=payload, 
                    headers=HEADERS, 
                    timeout=5
                )
                if res.status_code == 200:
                    print(f"Renewed lease for task #{self.task_id}", flush=True)
                elif res.status_code == 409:
                    print(f"Lease renewal rejected for task #{self.task_id}", flush=True)
                    self.aborted = True
                    break
                else:
                    print(f"[{WORKER_ID}] Lease renewal for task #{self.task_id} returned {res.status_code}: {res.text}", flush=True)
            except Exception as e:
                print(f"[{WORKER_ID}] Error renewing lease for task #{self.task_id}: {e}", flush=True)

    def stop(self):
        self.stop_event.set()

def execute_task(task: Any):
    from context.artifact_store import load_artifact_from_disk, save_artifact_to_disk
    task_type = task['type']
    task_data = task['data']
    task_id = task['id']
    retry_count = task.get('retry_count', 0)
    priority = task.get('priority', 'medium')
    
    print(f"[{WORKER_ID}] [{datetime.now().strftime('%H:%M:%S')}] Executing task {task_id}: {task_type} [Priority: {priority.upper()}] (Attempt {retry_count + 1})", flush=True)
    
    if current_renewer and current_renewer.aborted:
        raise Exception("Task execution aborted: lease expired or rejected.")

    simulate_hang_seconds = task_data.get('simulate_hang_seconds')
    if simulate_hang_seconds is not None:
        try:
            hang_time = float(simulate_hang_seconds)
            print(f"[{WORKER_ID}]   [HANG] [Simulation] Hanging task for {hang_time} seconds...", flush=True)
            start_hang = time.time()
            while time.time() - start_hang < hang_time:
                if current_renewer and current_renewer.aborted:
                    print(f"[{WORKER_ID}]   [HANG] Aborting hang simulation: lease rejected!", flush=True)
                    break
                time.sleep(0.5)
            if current_renewer and current_renewer.aborted:
                raise Exception("Task execution aborted during hang: lease expired or rejected.")
            print(f"[{WORKER_ID}]   [HANG] [Simulation] Wake up after hang!", flush=True)
        except (ValueError, TypeError):
            print(f"[{WORKER_ID}]   [WARN] Invalid simulate_hang_seconds value: {simulate_hang_seconds}", flush=True)

    if current_renewer and current_renewer.aborted:
        raise Exception("Task execution aborted: lease expired or rejected.")

    # Task types that are part of real pipeline and should not be randomly failed
    REAL_PIPELINE_TASK_TYPES = {
        "preprocess_document",
        "parse_document",
        "validate_parse_quality",
        "chunk_text",
        "generate_embeddings",
        "build_bm25_index",
        "summarize_document",
        "embed_query",
        "retrieve_context",
        "generate_answer_report"
    }

    if task_type not in REAL_PIPELINE_TASK_TYPES and random.random() < 0.1 and retry_count < 2:
        print(f"[{WORKER_ID}]   [FAIL] Task failed! Will retry...", flush=True)
        raise Exception(f"Simulated failure for task {task_id}")
    
    handler: Any = TASK_HANDLERS.get(task_type)
    if not handler:
        registry_info = TASK_REGISTRY.get(task_type, {})
        handler_name = registry_info.get("handler_name")
        if handler_name and isinstance(handler_name, str):
            handler = globals().get(handler_name)
            
    if handler:
        if task_type in OUTPUT_ARTIFACT_TYPES:
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
            
            if isinstance(task_data, dict):
                task_data['_task_id'] = task_id
                task_data['_pipeline_id'] = task.get('pipeline_id')
                task_data['_lease_token'] = task.get('lease_token')
                task_data['_progress_json'] = task.get('progress_json')
            
            if current_renewer and current_renewer.aborted:
                raise Exception("Task execution aborted: lease expired or rejected.")
                
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                handler_any: Any = handler
                future = executor.submit(handler_any, task_data, input_artifacts)
                try:
                    output_data = future.result(timeout=1800)
                except concurrent.futures.TimeoutError:
                    print(f"[{WORKER_ID}] [TIMEOUT] Task {task_id} exceeded 1800s limit!", flush=True)
                    raise Exception("Task timed out after 1800 seconds (Worker Deadlock Prevented)")

            if current_renewer and current_renewer.aborted:
                raise Exception("Task execution aborted: lease expired or rejected.")
            
            pipeline_id = task.get('pipeline_id')
            artifact_type = OUTPUT_ARTIFACT_TYPES[task_type]
            storage_uri, checksum = save_artifact_to_disk(pipeline_id, task_id, artifact_type, output_data)
            
            metadata = {"worker_id": WORKER_ID}
            if isinstance(output_data, dict):
                for k, v in output_data.items():
                    if k not in ["chunk_refs", "vectors", "embeddings"]:
                        metadata[k] = v
            elif isinstance(output_data, list):
                metadata["chunk_count"] = len(output_data)
                        
            res_reg = requests.post(
                f"{API_URL}/artifacts",
                json={
                    "pipeline_id": pipeline_id,
                    "task_id": task_id,
                    "artifact_type": artifact_type,
                    "storage_uri": storage_uri,
                    "checksum": checksum,
                    "metadata": metadata
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

def register_worker():
    print(f"[{WORKER_ID}] Registering worker with backend at {API_URL}...", flush=True)
    while True:
        try:
            payload = {
                "worker_id": WORKER_ID,
                "capabilities": WORKER_CAPABILITIES,
                "resource_limits": {"concurrency": 1}
            }
            res = requests.post(f"{API_URL}/workers/register", json=payload, headers=HEADERS, timeout=5)
            if res.status_code in [200, 201]:
                print(f"[{WORKER_ID}] Registered with capabilities: {WORKER_CAPABILITIES}", flush=True)
                break
            else:
                print(f"[{WORKER_ID}] Registration failed (status {res.status_code}): {res.text}. Retrying in 2s...", flush=True)
        except Exception as e:
            print(f"[{WORKER_ID}] Registration error: {e}. Retrying in 2s...", flush=True)
        time.sleep(2)

def get_next_task():
    try:
        try:
            paused_queues_raw = redis_client.smembers("scaleflow:paused_queues")
            paused_queues_raw_any: Any = paused_queues_raw
            if not paused_queues_raw_any:
                paused_queues = set()
            else:
                paused_queues = {q.decode() if isinstance(q, bytes) else str(q) for q in paused_queues_raw_any}
        except Exception:
            paused_queues = set()

        cycle_priorities = ['high', 'high', 'high', 'high', 'high', 'high', 'medium', 'medium', 'medium', 'low']
        wrr_val_raw = redis_client.incr('wrr_index')
        wrr_val: Any = wrr_val_raw
        wrr_idx = int(wrr_val) % len(cycle_priorities)
        target_priority = cycle_priorities[wrr_idx]
        
        for is_test in [True, False]:
            for cap in WORKER_CAPABILITIES:
                q_name = f"task_queue_test_{cap}_{target_priority}" if is_test else f"task_queue_{cap}_{target_priority}"
                if q_name in paused_queues:
                    continue
                val = redis_client.rpop(q_name)
                if val:
                    return (q_name, val)
                    
        for p in ['high', 'medium', 'low']:
            if p == target_priority:
                continue
            for is_test in [True, False]:
                for cap in WORKER_CAPABILITIES:
                    q_name = f"task_queue_test_{cap}_{p}" if is_test else f"task_queue_{cap}_{p}"
                    if q_name in paused_queues:
                        continue
                    val = redis_client.rpop(q_name)
                    if val:
                        return (q_name, val)
                        
        active_queues = [q for q in ALL_WORKER_QUEUES if q not in paused_queues]
        if active_queues:
            result = redis_client.brpop(active_queues, timeout=5)
            if result:
                return result
    except RedisConnectionError as ce:
        print(f"[{WORKER_ID}] Redis connection error during task pop: {ce}. Will retry shortly.", flush=True)
        time.sleep(3)
        return None
    except RedisTimeoutError:
        pass
    except Exception as e:
        print(f"[{WORKER_ID}] Error in get_next_task: {e}", flush=True)
        traceback.print_exc()
    return None

def worker_loop():
    worker_state['last_action'] = 'Registering worker'
    print(f"[{WORKER_ID}] Worker started! Verifying Redis connection...", flush=True)
    max_redis_retries = 12
    for attempt in range(1, max_redis_retries + 1):
        try:
            redis_client.ping()
            print(f"[{WORKER_ID}] Connected to Redis successfully!", flush=True)
            break
        except Exception as e:
            wait = min(2 ** attempt, 30)
            if attempt < max_redis_retries:
                print(f"[{WORKER_ID}] Redis not ready (attempt {attempt}/{max_redis_retries}): {e}. Retrying in {wait}s...", flush=True)
                time.sleep(wait)
            else:
                print(f"[{WORKER_ID}] CRITICAL: Could not reach Redis after {max_redis_retries} attempts: {e}. Worker will attempt to continue anyway.", flush=True)
    
    register_worker()
    print(f"[{WORKER_ID}] Listening on capability queues: {ALL_WORKER_QUEUES}", flush=True)
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
                
                max_attempts = 5
                response = None
                for attempt in range(max_attempts):
                    try:
                        response = requests.post(f"{API_URL}/tasks/{task_id}/claim", json={'worker_id': WORKER_ID}, headers=HEADERS, timeout=15)
                    except requests.exceptions.Timeout:
                        print(f"[{WORKER_ID}] Claim attempt {attempt+1} timed out for task #{task_id}", flush=True)
                        response = None
                        time.sleep(0.5)
                        continue
                    except requests.exceptions.ConnectionError as ce:
                        print(f"[{WORKER_ID}] Claim connection error for task #{task_id}: {ce}", flush=True)
                        response = None
                        time.sleep(1)
                        continue
                    if response.status_code == 200:
                        break
                    elif response.status_code == 400 and attempt < max_attempts - 1:
                        time.sleep(0.2)
                    else:
                        break
                
                if not response or response.status_code != 200:
                    worker_state['last_action'] = f"Failed to claim task #{task_id}"
                    status_code = response.status_code if response else "No Response"
                    text = response.text if response else ""
                    print(f"[{WORKER_ID}] Claim failed: {status_code} - {text}", flush=True)
                    continue
                    
                task = response.json()
                lease_token = task.get('lease_token')
                task_type = task.get('type')
                
                worker_state['last_action'] = f"Executing task #{task_id}"
                print(f"[{WORKER_ID}] Starting task {task_id} ({task_type})...", flush=True)
                worker_state['status'] = 'busy'
                worker_state['current_task_id'] = task_id
                
                global current_renewer
                current_renewer = LeaseRenewer(task_id, task_type, lease_token)
                current_renewer.start()
                
                try:
                    retry_count = task.get('retry_count', 0)
                    if retry_count > 0:
                        delay = min(2 ** retry_count, 30)
                        worker_state['last_action'] = f"Backing off task #{task_id} for {delay}s"
                        print(f"[{WORKER_ID}] Waiting {delay}s backoff before retry...", flush=True)
                        start_sleep = time.time()
                        while time.time() - start_sleep < delay:
                            if current_renewer.aborted:
                                break
                            time.sleep(0.5)
                        worker_state['last_action'] = f"Executing task #{task_id}"
                    
                    if current_renewer.aborted:
                        raise Exception("Task lease renewal was rejected (lease expired or worker mismatch) during backoff")
                        
                    execute_task(task)
                    
                    current_renewer.stop()
                    current_renewer.join(timeout=2)
                    
                    if current_renewer.aborted:
                        print(f"[{WORKER_ID}] Skipping task completion PATCH for task #{task_id} due to lease rejection.", flush=True)
                    else:
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
                    current_renewer.stop()
                    current_renewer.join(timeout=2)
                    
                    worker_state['last_action'] = f"Failed task #{task_id}"
                    print(f"[{WORKER_ID}] Failed task {task_id}: {str(e)}", flush=True)
                    
                    if current_renewer.aborted:
                        print(f"[{WORKER_ID}] Skipping task failure PATCH for task #{task_id} due to lease rejection.", flush=True)
                    else:
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
    try:
        from services.embedding_service import get_embedding_model
        print(f"[{WORKER_ID}] [STARTUP] Preloading embedding model...", flush=True)
        get_embedding_model()
        print(f"[{WORKER_ID}] [STARTUP] Embedding model preloaded successfully!", flush=True)
        
        from services.reranker_service import get_reranker
        print(f"[{WORKER_ID}] [STARTUP] Preloading reranker model...", flush=True)
        get_reranker()
        print(f"[{WORKER_ID}] [STARTUP] Reranker model preloaded successfully!", flush=True)
    except Exception as e:
        print(f"[{WORKER_ID}] [STARTUP] ERROR preloading models: {e}", flush=True)
    worker_loop()