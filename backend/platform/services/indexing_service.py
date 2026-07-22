from typing import Optional, Dict, Any
from backend.platform.services.index_manager import IndexManager

class IndexingService:
    def __init__(self, queue, index_manager: IndexManager):
        self.queue = queue
        self.manager = index_manager

    def submit_indexing_job(self, document_id: str, filepath: str) -> str:
        job_id = f"job_idx_{document_id}"
        payload = {
            "document_id": document_id,
            "filepath": filepath
        }
        self.queue.enqueue("indexing", payload, job_id=job_id)
        return job_id

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self.queue.get_status(job_id)
