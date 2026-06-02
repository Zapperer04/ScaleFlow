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
    try:
        with open('.env') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, val = line.strip().split('=', 1)
                    os.environ.setdefault(key.strip(), val.strip())
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

# Build the complete list of matching queues for the worker
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
def get_uploaded_file_path(pipeline_id):
    try:
        res = requests.get(f"{API_URL}/pipelines/{pipeline_id}", headers=HEADERS, timeout=5)
        if res.status_code == 200:
            data = res.json()
            for art in data.get("artifacts", []):
                if art.get("artifact_type") == "uploaded_file":
                    storage_uri = art.get("storage_uri")
                    from context.artifact_store import BASE_STORAGE_DIR
                    if storage_uri.startswith("storage/"):
                        rel_path = storage_uri[len("storage/"):]
                    elif storage_uri.startswith("storage\\"):
                        rel_path = storage_uri[len("storage\\"):]
                    else:
                        rel_path = storage_uri
                    # Normalize separators for cross-platform compliance
                    rel_path = rel_path.replace("\\", "/")
                    full_path = os.path.normpath(os.path.join(BASE_STORAGE_DIR, rel_path))
                    return full_path
    except Exception as e:
        print(f"[{WORKER_ID}] Error fetching uploaded file path: {e}", flush=True)
    return None

# ─────────────────────────────────────────────────────────────────────────────
# PDF parsing delegated to services/pdf_parser.py (fallback chain)
# ─────────────────────────────────────────────────────────────────────────────
def handle_parse_document(payload, input_artifacts):
    """
    Parse uploaded document via a 3-tier fallback chain:
    pypdf → pdfplumber → OCR (scanned/image pages only).
    All parser decisions are emitted as task trace events.
    """
    text = payload.get('source_text')
    pipeline_id = payload.get('_pipeline_id')
    task_id = payload.get('_task_id')
    lease_token = payload.get('_lease_token')
    progress_json = payload.get('_progress_json')
    parse_stats = {}

    def _trace(msg: str):
        print(f"[{WORKER_ID}] {msg}", flush=True)
        emit_task_trace(task_id, msg)

    if not text and pipeline_id:
        _trace("[PARSER] Initializing document parser")
        filepath = get_uploaded_file_path(pipeline_id)
        if filepath and os.path.exists(filepath):
            file_id, original_filename, _ = get_pipeline_file_info(pipeline_id)
            is_pdf = (
                (original_filename and original_filename.lower().endswith(".pdf"))
                or filepath.lower().endswith(".pdf")
            )

            if is_pdf:
                _trace(f"[PARSER] PDF detected — starting fallback-chain parser")
                try:
                    from services.pdf_parser import parse_pdf
                    result = parse_pdf(
                        filepath=filepath,
                        task_id=task_id,
                        lease_token=lease_token,
                        progress_json=progress_json if isinstance(progress_json, dict) else {},
                        trace_fn=_trace,
                        api_url=API_URL,
                        api_headers=HEADERS,
                    )
                    text = result.text
                    parse_stats = result.stats

                    if not text:
                        _trace("[PARSER] WARNING: All parsers returned empty text. Document may be fully graphical.")
                except ValueError as ve:
                    # Circuit-breaker / validation failure — surface clearly
                    _trace(f"[PARSER] VALIDATION FAILURE: {ve}")
                    raise
                except TimeoutError as te:
                    _trace(f"[PARSER] TIMEOUT: {te}")
                    raise Exception(str(te))
                except Exception as e:
                    _trace(f"[PARSER] CRITICAL ERROR: {e}")
                    raise
            else:
                # Plain text / log file
                _trace("[PARSER] Plain-text file detected — reading directly")
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                    _trace(f"[PARSER] Read {len(text)} chars from file")
                except Exception as e:
                    _trace(f"[PARSER] ERROR reading file: {e}")
        else:
            if filepath:
                _trace(f"[PARSER] ERROR: File not found at expected path: {filepath}")
            else:
                _trace("[PARSER] ERROR: Could not resolve file path from pipeline artifacts")

    # Fallback to raw artifact content (used in unit tests / inline pipelines)
    if not text and input_artifacts:
        uploaded_file_data = input_artifacts.get("uploaded_file")
        if uploaded_file_data is not None:
            text = str(uploaded_file_data)
        elif input_artifacts:
            first_val = list(input_artifacts.values())[0]
            text = first_val.get("content", str(first_val)) if isinstance(first_val, dict) else str(first_val)

    if not text:
        text = ""

    normalized = text.strip()
    _trace(f"[PARSER] Complete — extracted {len(normalized):,} characters")
    if parse_stats.get("ocr_pages", 0) > 0:
        _trace(f"[PARSER] OCR was used on {parse_stats['ocr_pages']} page(s)")
    if parse_stats.get("page_failures"):
        for pf in parse_stats["page_failures"][:5]:   # surface first 5 only
            _trace(f"[PARSER] Page {pf['page']} failure [{pf['parser']}]: {pf['reason'][:120]}")

    # Return text with embedded parse stats so the artifact metadata carries them
    return {"parsed_text": normalized, "parse_stats": parse_stats}


def handle_validate_parse_quality(payload, input_artifacts):
    """
    Quality Gate verifying the parsed document text before chunking.
    Calculates OCR confidence, printable character ratio, dictionary-word ratio, and text coherence score.
    """
    task_id = payload.get('_task_id')
    pipeline_id = payload.get('_pipeline_id')
    
    def _trace(msg: str):
        print(f"[{WORKER_ID}] {msg}", flush=True)
        emit_task_trace(task_id, msg)
        
    _trace("[QUALITY GATE] Starting parse quality validation gate...")
    
    # 1. Fetch text from parsed_text input artifact
    raw_input = input_artifacts.get("parsed_text", "")
    if isinstance(raw_input, dict):
        text = raw_input.get("parsed_text", "")
        parse_stats = raw_input.get("parse_stats", {})
    else:
        text = raw_input
        parse_stats = {}
        
    if not text:
        text = payload.get("source_text", "")
        
    if not text:
        _trace("[QUALITY GATE] FAILED: No text was extracted from the document.")
        raise ValueError("Document unreadable / OCR quality too low: Extracted text is empty.")

    from services.quality_gate_service import validate_quality
    try:
        metrics = validate_quality(text, parse_stats)
        
        # Emit tracing
        _trace(f"[QUALITY GATE] Ingestion Parser Used: {metrics['parser_used'].upper()}")
        _trace(f"[QUALITY GATE] OCR Activation Status: {'YES' if metrics['ocr_activated'] else 'NO'}")
        _trace(f"[QUALITY GATE] Average OCR Confidence Score: {metrics['ocr_confidence']:.1f}%")
        _trace(f"[QUALITY GATE] Executing Quality Gate Decisions:")
        _trace(f"  - Printable Character Ratio: {metrics['printable_ratio']:.2%} (Min Threshold: {config.MIN_PRINTABLE_RATIO:.2%})")
        _trace(f"  - Dictionary-Word Ratio: {metrics['dict_word_ratio']:.2%} (Min Threshold: {config.MIN_DICTIONARY_WORD_RATIO:.2%})")
        _trace(f"  - Text Coherence Score: {metrics['coherence_score']:.1f}/100.0 (Min Threshold: {config.MIN_TEXT_COHERENCE_SCORE:.1f})")
        
        _trace("[QUALITY GATE] PASSED: Document parsing quality is within acceptable bounds.")
        return metrics
    except ValueError as ve:
        _trace(f"[QUALITY GATE] FAILED: {str(ve)}")
        raise ve


# ─────────────────────────────────────────────────────────────────────────────
# Semantic Chunker — paragraph-aware, sentence-boundary-preserving
# ─────────────────────────────────────────────────────────────────────────────
def handle_chunk_text(payload, input_artifacts):
    """
    Paragraph-aware, sentence-boundary-preserving semantic chunker.
    Replaces the old fixed sliding-window approach.
    """
    task_id = payload.get('_task_id')

    # Input may be a dict (new format from handle_parse_document) or raw string
    raw_input = input_artifacts.get("parsed_text", "")
    if isinstance(raw_input, dict):
        text = raw_input.get("parsed_text", "")
    elif isinstance(raw_input, str):
        text = raw_input
    else:
        text = payload.get("source_text", "")

    if not text:
        text = payload.get("source_text", "")

    emit_task_trace(task_id, "[CHUNKER] Paragraph-aware semantic chunking started")

    # Detect paragraph structure richness
    paragraph_count = len([p for p in re.split(r'\n{2,}', text) if p.strip()])
    emit_task_trace(task_id, f"[CHUNKER] Detected {paragraph_count} paragraphs in document")

    from services.chunking_service import chunk_text
    
    t_start = time.perf_counter()
    chunks = chunk_text(text)
    duration = time.perf_counter() - t_start

    if chunks:
        avg_words = sum(len(c.split()) for c in chunks) // len(chunks)
    else:
        avg_words = 0

    emit_task_trace(task_id, f"[CHUNKER] Generated {len(chunks)} chunks (avg {avg_words} words/chunk)")
    emit_task_trace(task_id, f"[PROFILE] chunking_duration={duration:.5f}s count={len(chunks)}")
    print(f"[{WORKER_ID}]   [OK] Chunked text into {len(chunks)} semantic chunks (avg {avg_words} words) (took {duration:.4f}s)", flush=True)
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
    from services.embedding_service import embed_chunks_with_progress, get_model_load_time
    from services.vector_store import upsert_document_chunks

    task_id     = payload.get('_task_id')
    pipeline_id = payload.get('_pipeline_id')

    MAX_EMBED_CHUNKS = config.MAX_CHUNKS

    def _trace(msg: str):
        print(f"[{WORKER_ID}] {msg}", flush=True)
        emit_task_trace(task_id, msg)

    # ── normalise input (text_chunks or error_patterns) ──────────────────────
    raw = input_artifacts.get("text_chunks") or input_artifacts.get("error_patterns") or []
    if isinstance(raw, str):
        chunks = [raw]
    elif isinstance(raw, dict):
        chunks = [json.dumps(raw)]
    elif isinstance(raw, list):
        # Each element may itself be a string or dict
        chunks = [c if isinstance(c, str) else json.dumps(c) for c in raw]
    else:
        chunks = []

    # ── resource guard: cap chunk count ──────────────────────────────────────
    if len(chunks) > MAX_EMBED_CHUNKS:
        _trace(f"[EMBED] WARNING: {len(chunks)} chunks exceeds limit {MAX_EMBED_CHUNKS}. Truncating.")
        chunks = chunks[:MAX_EMBED_CHUNKS]

    _trace(f"[EMBED] Generating embeddings for {len(chunks)} chunks (model: {config.EMBEDDING_MODEL}, dim={config.EMBEDDING_DIMENSION})")

    # ── generate embeddings with batch progress trace ─────────────────────────
    vectors = []
    embed_generation_duration = 0.0
    model_load_duration = 0.0
    if chunks:
        def _batch_trace(batch_num, total_batches, done, total):
            # Print to stdout directly (fast, local)
            print(f"[{WORKER_ID}] [EMBED] Batch {batch_num}/{total_batches} — {done}/{total} chunks embedded", flush=True)
            # Throttle HTTP traces to reduce network overhead: only post on first, last, and every 5th batch
            if batch_num == 1 or batch_num == total_batches or batch_num % 5 == 0:
                emit_task_trace(task_id, f"[EMBED] Batch {batch_num}/{total_batches} — {done}/{total} chunks embedded")

        t_embed_start = time.perf_counter()
        vectors = embed_chunks_with_progress(chunks, progress_callback=_batch_trace, batch_size=config.EMBEDDING_BATCH_SIZE)
        embed_generation_duration = time.perf_counter() - t_embed_start
        model_load_duration = get_model_load_time()

    # ── resolve pipeline context ──────────────────────────────────────────────
    file_id = original_filename = source_artifact_id = None
    if pipeline_id:
        file_id, original_filename, source_artifact_id = get_pipeline_file_info(pipeline_id)

    # ── upsert to Qdrant ──────────────────────────────────────────────────────
    qdrant_upserted = False
    qdrant_lookup_duration = 0.0
    qdrant_insertion_duration = 0.0
    if chunks and vectors:
        _trace(f"[QDRANT] Upserting {len(chunks)} vectors to collection 'scaleflow_chunks'...")
        meta_dict = {
            "source_artifact_id": source_artifact_id,
            "original_filename":  original_filename
        }
        qdrant_upserted, qdrant_lookup_duration, qdrant_insertion_duration = upsert_document_chunks(
            pipeline_id=pipeline_id,
            file_id=file_id,
            task_id=task_id,
            chunks=chunks,
            vectors=vectors,
            metadata=meta_dict
        )
        if qdrant_upserted:
            _trace(f"[QDRANT] Insertion complete — {len(chunks)} vectors indexed")
        else:
            _trace("[QDRANT] WARNING: Upsert returned False — check Qdrant connectivity")

    # ── build artifact data ───────────────────────────────────────────────────
    chunk_refs = [
        {"chunk_index": idx, "chunk_text": (c[:120] + "...") if len(c) > 120 else c}
        for idx, c in enumerate(chunks)
    ]

    artifact_data = {
        "collection":      "scaleflow_chunks",
        "vector_count":    len(chunks),
        "embedding_model": config.EMBEDDING_MODEL,
        "dimension":       config.EMBEDDING_DIMENSION,
        "qdrant_upserted": qdrant_upserted,
        "chunk_refs":      chunk_refs,
        "model_load_duration": round(model_load_duration, 5),
        "embedding_generation_duration": round(embed_generation_duration, 5),
        "batch_size_used": config.EMBEDDING_BATCH_SIZE,
        "total_chunks_embedded": len(chunks),
        "qdrant_collection_lookup_duration": round(qdrant_lookup_duration, 5),
        "qdrant_insertion_duration": round(qdrant_insertion_duration, 5)
    }

    _trace(f"[PROFILE] model_load_duration={model_load_duration:.5f}s embedding_generation_duration={embed_generation_duration:.5f}s qdrant_lookup_duration={qdrant_lookup_duration:.5f}s qdrant_insertion_duration={qdrant_insertion_duration:.5f}s")
    _trace(f"[EMBED] Complete — {len(chunks)} vectors (qdrant_upserted={qdrant_upserted})")
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
                
            if isinstance(text, dict):
                text = text.get("parsed_text", "")
                
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
        "embedding_model": "all-MiniLM-L6-v2",
        "dimension": 384,
        "vector": vector,
        "top_k": payload.get("top_k"),
        "pipeline_id_filter": payload.get("pipeline_id_filter"),
        "file_id_filter": payload.get("file_id_filter")
    }
    print(f"[{WORKER_ID}] [OK] Generated query vector for query: {query[:50]}...", flush=True)
    return artifact_data

def is_general_query(query: str) -> bool:
    if not query:
        return False
    q = query.lower().strip("?. ")
    general_phrases = [
        "what is it about",
        "what is this document about",
        "what is this about",
        "summarize",
        "summary",
        "give me a summary",
        "what does it talk about",
        "what is this",
        "tell me about this",
        "what is the document about",
        "what is the file about",
        "summarize this document",
        "summarize this file"
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
    pipeline_id_filter = query_vector_data.get("pipeline_id_filter")
    
    p_id = to_int_or_none(pipeline_id_filter)
    if p_id is None:
        raise ValueError("Document-scoped retrieval failed: 'pipeline_id_filter' is missing or invalid.")
        
    print("=" * 80, flush=True)
    print("RETRIEVAL TASK INITIATED", flush=True)
    print(f"QUERY: {query}", flush=True)
    print(f"PIPELINE FILTER: {p_id}", flush=True)
    print(f"TOP-K: {top_k}", flush=True)
    print("=" * 80, flush=True)
        
    from services.retrieval_service import retrieve_context
    artifact_data = retrieve_context(query_vector=vector, pipeline_id=p_id, top_k=top_k, query=query)
    
    filtered_results = artifact_data.get("results", [])
    print(f"[{WORKER_ID}] [OK] Retrieved {len(filtered_results)} context chunks", flush=True)
    return artifact_data

def handle_generate_answer_report(payload, input_artifacts):
    context_data = input_artifacts.get("retrieved_context")
    if not context_data:
        raise ValueError("Missing 'retrieved_context' in generate_answer_report input artifacts")
        
    query = context_data.get("query", "")
    results: list[Any] = context_data.get("results", [])
    
    # Verify score threshold or summary chunk
    min_score = float(os.getenv("MIN_RETRIEVAL_SCORE", "0.3"))
    valid_results = [r for r in results if float(r.get("score") or 0.0) >= min_score or r.get("chunk_index") == -1]
    
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

    confidence = "low"
    if valid_results:
        top_score = valid_results[0].get("score", 0.0)
        if top_score >= 0.8:
            confidence = "high"
        elif top_score >= 0.6:
            confidence = "medium"
            
    top_chunks = valid_results[:3]
    if not top_chunks:
        answer = "No sufficiently relevant context was found for this query."
        citations = []
        confidence = "low"
    else:
        answer_parts = []
        citations = []
        seen_citations = set()
        for idx, hit in enumerate(top_chunks):
            chunk_text = hit.get("chunk_text", "").strip()
            score = hit.get("score", 0.0)
            fname = hit.get("original_filename") or "unknown_file"
            fid = hit.get("file_id")
            cidx = hit.get("chunk_index", 0)
            
            if cidx == -1:
                # It's an injected summary chunk
                cleaned_text = chunk_text.replace("Document Summary:", "").strip()
                answer_parts.append(f"Auto-generated Document Summary (Confidence Score: {score}):\n{cleaned_text}")
            else:
                answer_parts.append(f"Source [{idx+1}] (Confidence Score: {score}): \"{chunk_text}\"")
            
            citation_key = (fid, cidx)
            if citation_key not in seen_citations:
                seen_citations.add(citation_key)
                citations.append({
                    "file_id": fid,
                    "original_filename": fname,
                    "chunk_index": cidx
                })
        
        answer = f"Based on the retrieved context, here are the most relevant sections matching your query:\n\n" + "\n\n".join(answer_parts)
        
    artifact_data = {
        "query": query,
        "answer": answer,
        "citations": citations,
        "confidence": confidence
    }
    print(f"[{WORKER_ID}] [OK] Generated final answer with {len(citations)} citations and confidence '{confidence}'", flush=True)
    return artifact_data

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
    "generate_answer_report": handle_generate_answer_report
}

OUTPUT_ARTIFACT_TYPES = {
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
    "generate_answer_report": "final_answer"
}

LEASE_DURATIONS = {
    "send_email": 30,
    "process_video": 120,
    "generate_report": 60,
    "parse_document": 60,
    "validate_parse_quality": 60,
    "chunk_text": 60,
    "generate_embeddings": 180,
    "summarize_document": 60,
    "parse_logs": 60,
    "detect_error_patterns": 60,
    "summarize_logs": 60,
    "final_report": 60,
    "embed_query": 60,
    "retrieve_context": 60,
    "generate_answer_report": 60
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
        interval = max(1, lease_duration // 2)
        
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
    """Simulate doing the actual work - with random failures for testing retry"""
    from context.artifact_store import load_artifact_from_disk, save_artifact_to_disk
    task_type = task['type']
    task_data = task['data']
    task_id = task['id']
    retry_count = task.get('retry_count', 0)
    priority = task.get('priority', 'medium')
    
    print(f"[{WORKER_ID}] [{datetime.now().strftime('%H:%M:%S')}] Executing task {task_id}: {task_type} [Priority: {priority.upper()}] (Attempt {retry_count + 1})", flush=True)
    
    if current_renewer and current_renewer.aborted:
        raise Exception("Task execution aborted: lease expired or rejected.")

    # Check for simulate_hang_seconds in payload
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

    # Simulated random failure applies ONLY to demo/simulation task types.
    # Real AI pipeline tasks (document ingestion & RAG retrieval) must never be randomly failed.
    REAL_PIPELINE_TASK_TYPES = {
        "parse_document", "chunk_text", "generate_embeddings", "summarize_document",
        "embed_query", "retrieve_context", "generate_answer_report"
    }
    if task_type not in REAL_PIPELINE_TASK_TYPES and random.random() < 0.1 and retry_count < 2:
        print(f"[{WORKER_ID}]   [FAIL] Task failed! Will retry...", flush=True)
        raise Exception(f"Simulated failure for task {task_id}")
    
    # Check in handler map
    handler: Any = HANDLER_MAP.get(task_type)
    if not handler:
        registry_info = TASK_REGISTRY.get(task_type, {})
        handler_name = registry_info.get("handler_name")
        if handler_name and isinstance(handler_name, str):
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
                task_data['_lease_token'] = task.get('lease_token')
                task_data['_progress_json'] = task.get('progress_json')
            
            if current_renewer and current_renewer.aborted:
                raise Exception("Task execution aborted: lease expired or rejected.")
                
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                handler_any: Any = handler
                future = executor.submit(handler_any, task_data, input_artifacts)
                try:
                    output_data = future.result(timeout=300)
                except concurrent.futures.TimeoutError:
                    print(f"[{WORKER_ID}] [TIMEOUT] Task {task_id} exceeded 300s limit!", flush=True)
                    raise Exception("Task timed out after 300 seconds (Worker Deadlock Prevented)")

            if current_renewer and current_renewer.aborted:
                raise Exception("Task execution aborted: lease expired or rejected.")
            
            # Save artifact to disk
            pipeline_id = task.get('pipeline_id')
            artifact_type = OUTPUT_ARTIFACT_TYPES[task_type]
            storage_uri, checksum = save_artifact_to_disk(pipeline_id, task_id, artifact_type, output_data)
            
            # Register artifact with API, preserving metadata from output dict
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
    """Registers worker and its capabilities with the orchestrator, retrying until success"""
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
    """Get next task using capability-aware Weighted Round-Robin (WRR) scheduling"""
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
        # Atomic increment wrr_index in Redis
        wrr_val_raw = redis_client.incr('wrr_index')
        wrr_val: Any = wrr_val_raw
        wrr_idx = int(wrr_val) % len(cycle_priorities)
        target_priority = cycle_priorities[wrr_idx]
        
        # 1. Try to pop from target priority queues matching capabilities (test first, then prod)
        for is_test in [True, False]:
            for cap in WORKER_CAPABILITIES:
                q_name = f"task_queue_test_{cap}_{target_priority}" if is_test else f"task_queue_{cap}_{target_priority}"
                if q_name in paused_queues:
                    continue
                val = redis_client.rpop(q_name)
                if val:
                    return (q_name, val)
                    
        # 2. Fall back to priority order non-blockingly to prevent starvation
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
                        
        # 3. If all queues are empty, block on brpop of active (non-paused) worker queues
        active_queues = [q for q in ALL_WORKER_QUEUES if q not in paused_queues]
        if active_queues:
            result = redis_client.brpop(active_queues, timeout=5)
            if result:
                return result
    except RedisConnectionError as ce:
        print(f"[{WORKER_ID}] Redis connection error during task pop: {ce}", flush=True)
        raise ce
    except RedisTimeoutError:
        pass
    except Exception as e:
        print(f"[{WORKER_ID}] Error in get_next_task: {e}", flush=True)
        traceback.print_exc()
    return None

def worker_loop():
    worker_state['last_action'] = 'Registering worker'
    print(f"[{WORKER_ID}] Worker started! Verifying Redis connection...", flush=True)
    try:
        redis_client.ping()
        print(f"[{WORKER_ID}] Connected to Redis successfully!", flush=True)
    except Exception as e:
        print(f"[{WORKER_ID}] CRITICAL: Failed to connect to Redis: {e}", flush=True)
    
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
                
                # Retry claim in case of DB transaction commit race condition
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
                        # Sleep briefly and retry
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
        print(f"[{WORKER_ID}] [STARTUP] Preloading embedding model: all-MiniLM-L6-v2...", flush=True)
        get_embedding_model()
        print(f"[{WORKER_ID}] [STARTUP] Embedding model preloaded successfully!", flush=True)
    except Exception as e:
        print(f"[{WORKER_ID}] [STARTUP] ERROR preloading embedding model: {e}", flush=True)
    worker_loop()