import json
import uuid
from typing import Dict, Any, Optional
from backend.platform.scheduler.queue_interface import QueueInterface
from backend.platform.runtime.app_state import app_state

class SQLiteQueue(QueueInterface):
    def __init__(self):
        pass

    def _get_conn(self):
        return app_state.db_conn

    def enqueue(self, task_type: str, payload: Dict[str, Any], job_id: str = None) -> str:
        jid = job_id or f"job_sql_{uuid.uuid4()}"
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO job_queue (id, task_type, payload_json, status)
        VALUES (?, ?, ?, 'queued')
        ON CONFLICT(id) DO UPDATE SET
            status = 'queued',
            attempts = 0,
            error = NULL,
            updated_at = CURRENT_TIMESTAMP
        """, (jid, task_type, json.dumps(payload)))
        conn.commit()
        return jid

    def dequeue(self) -> Optional[Dict[str, Any]]:
        conn = self._get_conn()
        if not conn:
            return None
        cursor = conn.cursor()
        
        # Select first queued job
        cursor.execute("""
        SELECT id, task_type, payload_json, attempts, max_attempts FROM job_queue
        WHERE status = 'queued' OR (status = 'failed' AND attempts < max_attempts)
        ORDER BY created_at ASC LIMIT 1
        """)
        row = cursor.fetchone()
        if row:
            job_id = row["id"]
            new_attempts = row["attempts"] + 1
            
            # Lock the job
            cursor.execute("""
            UPDATE job_queue SET status = 'running', attempts = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?
            """, (new_attempts, job_id))
            conn.commit()
            
            return {
                "job_id": job_id,
                "task_type": row["task_type"],
                "payload": json.loads(row["payload_json"])
            }
        return None

    def complete(self, job_id: str):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE job_queue SET status = 'completed', updated_at = CURRENT_TIMESTAMP WHERE id = ?
        """, (job_id,))
        conn.commit()

    def fail(self, job_id: str, error: str):
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Check attempts
        cursor.execute("SELECT attempts, max_attempts FROM job_queue WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        if row:
            attempts = row["attempts"]
            max_attempts = row["max_attempts"]
            # If exceeded, status stays failed. Otherwise goes back to queued to retry.
            next_status = "failed" if attempts >= max_attempts else "queued"
            
            cursor.execute("""
            UPDATE job_queue SET status = ?, error = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?
            """, (next_status, error, job_id))
            conn.commit()

    def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_conn()
        if not conn:
            return None
        cursor = conn.cursor()
        cursor.execute("SELECT id, status, attempts, error FROM job_queue WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        if row:
            return {
                "id": row["id"],
                "status": row["status"],
                "attempts": row["attempts"],
                "error": row["error"]
            }
        return None
