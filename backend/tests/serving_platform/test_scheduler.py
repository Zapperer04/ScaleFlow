import sys
import os
import pytest
import sqlite3
import tempfile
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from backend.platform.scheduler.sqlite_queue import SQLiteQueue
from backend.platform.runtime.app_state import app_state

@pytest.fixture
def temp_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE job_queue (
        id TEXT PRIMARY KEY,
        task_type TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        status TEXT NOT NULL,
        worker_id TEXT,
        attempts INTEGER DEFAULT 0,
        max_attempts INTEGER DEFAULT 3,
        error TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    original_db = app_state.db_conn
    app_state.db_conn = conn
    yield conn
    app_state.db_conn = original_db
    conn.close()

def test_sqlite_queue_operations(temp_db):
    queue = SQLiteQueue()
    
    # 1. Enqueue
    job_id = queue.enqueue("test_task", {"foo": "bar"}, job_id="my_job_1")
    assert job_id == "my_job_1"
    
    # Check status is queued
    status = queue.get_status(job_id)
    assert status["status"] == "queued"
    
    # 2. Dequeue
    task = queue.dequeue()
    assert task is not None
    assert task["job_id"] == "my_job_1"
    assert task["task_type"] == "test_task"
    assert task["payload"] == {"foo": "bar"}
    
    # Check status is running
    status = queue.get_status(job_id)
    assert status["status"] == "running"
    
    # 3. Fail (retry threshold not exceeded)
    queue.fail(job_id, "temporary error")
    status = queue.get_status(job_id)
    assert status["status"] == "queued" # Retries
    
    # 4. Dequeue again
    task = queue.dequeue()
    assert task is not None
    
    # 5. Fail (retry threshold exceeded)
    queue.fail(job_id, "terminal error") # 2nd fail, state goes back to queued
    task = queue.dequeue() # 3rd attempt, state running
    queue.fail(job_id, "terminal error") # 3rd fail, state failed
    status = queue.get_status(job_id)
    assert status["status"] == "failed"
