import os
import time
import uuid
import logging
import threading
from typing import Dict, Any, Optional
from backend.platform.runtime.app_state import app_state
from backend.platform.runtime.dependency_container import DependencyContainer
from backend.platform.streaming.event_bus import event_bus
from backend.platform.streaming.events import PlatformEvent, EVENT_INDEX_STARTED, EVENT_INDEX_COMPLETE
from backend.platform.security.audit import audit_logger

logger = logging.getLogger(__name__)

# Control variables
_worker_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()
WORKER_ID = f"worker_{uuid.uuid4().hex[:8]}"

def update_worker_heartbeat(status: str):
    conn = app_state.db_conn
    if not conn:
        return
    try:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO worker_registry (worker_id, status, last_heartbeat)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(worker_id) DO UPDATE SET
            status = excluded.status,
            last_heartbeat = CURRENT_TIMESTAMP
        """, (WORKER_ID, status))
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to update worker heartbeat: {e}")

def recover_running_jobs_on_restart():
    """
    Reset any jobs stuck in 'running' to 'queued' to resume execution.
    """
    conn = app_state.db_conn
    if not conn:
        return
    try:
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE job_queue SET status = 'queued' WHERE status = 'running'
        """)
        conn.commit()
        logger.info("Recovered stuck running jobs on startup.")
    except Exception as e:
        logger.error(f"Failed to recover running jobs: {e}")

def worker_loop():
    logger.info(f"Worker thread {WORKER_ID} loop started.")
    recover_running_jobs_on_restart()
    
    while not _stop_event.is_set():
        try:
            update_worker_heartbeat("idle")
            
            queue = app_state.queue
            if not queue:
                time.sleep(1.0)
                continue
                
            task = queue.dequeue()
            if not task:
                time.sleep(1.0)
                continue
                
            job_id = task["job_id"]
            task_type = task["task_type"]
            payload = task["payload"]
            
            update_worker_heartbeat("running")
            logger.info(f"Worker executing job {job_id} ({task_type})")
            
            if task_type == "indexing":
                execute_indexing_job(job_id, payload)
            else:
                logger.error(f"Unknown task type: {task_type}")
                queue.complete(job_id)
                
        except Exception as e:
            logger.error(f"Error in worker loop: {e}")
            time.sleep(1.0)
            
    update_worker_heartbeat("dead")
    logger.info("Worker thread loop stopped.")

def execute_indexing_job(job_id: str, payload: Dict[str, Any]):
    doc_id = payload["document_id"]
    filepath = payload["filepath"]
    
    doc_service = DependencyContainer.get_document_service()
    index_manager = DependencyContainer.get_index_manager()
    queue = app_state.queue
    
    doc_service.update_state(doc_id, "INDEXING")
    
    # Emit index started event
    event_bus.publish(PlatformEvent(EVENT_INDEX_STARTED, {"document_id": doc_id}))
    audit_logger.log_action("system_worker", "INDEX_START", doc_id, "SUCCESS")
    
    try:
        # Define progress tracker callback
        from backend.platform.streaming.progress_stream import ProgressTracker
        tracker = ProgressTracker(doc_id, callback=event_bus.publish)
        
        # Execute parsing and builder pipeline
        index_manager.run_indexing(doc_id, filepath, trace_fn=tracker.get_trace_fn())
        
        # Get versions to store
        versions = {
            "parser_version": "1.0.0",
            "embedding_version": "1.0.0",
            "chunk_version": "1.0.0",
            "graph_version": "1.0.0",
            "index_version": "1.0.0"
        }
        
        doc_service.update_state(doc_id, "INDEXED", versions=versions)
        queue.complete(job_id)
        
        # Emit complete event
        event_bus.publish(PlatformEvent(EVENT_INDEX_COMPLETE, {"document_id": doc_id}))
        audit_logger.log_action("system_worker", "INDEX_COMPLETE", doc_id, "SUCCESS")
        
    except Exception as e:
        logger.error(f"Failed to process document {doc_id}: {e}")
        doc_service.update_state(doc_id, "FAILED")
        queue.fail(job_id, str(e))
        audit_logger.log_action("system_worker", "INDEX_FAIL", doc_id, "FAILED", details=str(e))

def start_worker_thread() -> threading.Thread:
    global _worker_thread, _stop_event
    _stop_event.clear()
    _worker_thread = threading.Thread(target=worker_loop, daemon=True)
    _worker_thread.start()
    return _worker_thread

def stop_worker_thread():
    global _worker_thread, _stop_event
    if _worker_thread:
        _stop_event.set()
        _worker_thread.join(timeout=3.0)
        _worker_thread = None
