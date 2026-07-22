import uuid
import time
from typing import Dict, Any, Optional, List
from backend.platform.scheduler.queue_interface import QueueInterface

class MemoryQueue(QueueInterface):
    def __init__(self):
        self.queue: List[Dict[str, Any]] = []
        self.jobs: Dict[str, Dict[str, Any]] = {}

    def enqueue(self, task_type: str, payload: Dict[str, Any], job_id: str = None) -> str:
        jid = job_id or f"job_mem_{uuid.uuid4()}"
        job_data = {
            "id": jid,
            "task_type": task_type,
            "payload": payload,
            "status": "queued",
            "attempts": 0,
            "error": None,
            "created_at": time.time()
        }
        self.jobs[jid] = job_data
        self.queue.append(job_data)
        return jid

    def dequeue(self) -> Optional[Dict[str, Any]]:
        # Find first queued or retrying job
        for job in self.queue:
            if job["status"] in ("queued", "failed") and job["attempts"] < 3:
                job["status"] = "running"
                job["attempts"] += 1
                return {
                    "job_id": job["id"],
                    "task_type": job["task_type"],
                    "payload": job["payload"]
                }
        return None

    def complete(self, job_id: str):
        if job_id in self.jobs:
            self.jobs[job_id]["status"] = "completed"

    def fail(self, job_id: str, error: str):
        if job_id in self.jobs:
            job = self.jobs[job_id]
            job["error"] = error
            if job["attempts"] >= 3:
                job["status"] = "failed"
            else:
                job["status"] = "queued" # Eligible for retry

    def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        if job_id in self.jobs:
            j = self.jobs[job_id]
            return {
                "id": j["id"],
                "status": j["status"],
                "attempts": j["attempts"],
                "error": j["error"]
            }
        return None
