from collections import deque
from typing import Dict, List, Optional
from execution_engine.core.job import JobSpec

class InterleavedFairQueue:
    def __init__(self):
        self.doc_queues: Dict[str, deque] = {}
        self.doc_order: List[str] = []
        self.current_index = 0

    def push(self, job: JobSpec):
        doc_id = job.metadata.get("document_id", "default")
        if doc_id not in self.doc_queues:
            self.doc_queues[doc_id] = deque()
            self.doc_order.append(doc_id)
        self.doc_queues[doc_id].append(job)

    def pop(self) -> Optional[JobSpec]:
        if not self.doc_order:
            return None
        attempts = 0
        while attempts < len(self.doc_order):
            self.current_index = (self.current_index + 1) % len(self.doc_order)
            doc_id = self.doc_order[self.current_index]
            queue = self.doc_queues[doc_id]
            if queue:
                job = queue.popleft()
                if not queue:
                    del self.doc_queues[doc_id]
                    self.doc_order.remove(doc_id)
                    if self.current_index >= len(self.doc_order) and self.doc_order:
                        self.current_index = 0
                return job
            attempts += 1
        return None

    def size(self) -> int:
        return sum(len(q) for q in self.doc_queues.values())
