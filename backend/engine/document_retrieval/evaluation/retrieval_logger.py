import os
import json
import time
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class RetrievalLogger:
    def __init__(self, log_dir: str = None):
        if log_dir is None:
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            log_dir = os.path.join(current_dir, "storage", "document_store")
        os.makedirs(log_dir, exist_ok=True)
        self.log_path = os.path.join(log_dir, "retrieval_evaluation_logs.jsonl")

    def log_run(
        self,
        query: str,
        experts: List[str],
        evidence_count: int,
        expanded_evidence_count: int,
        candidate_count: int,
        fusion_score: float,
        agreement_score: float,
        final_ranking: List[str],
        latency: float,
        tokens: int,
        memory_usage_mb: float = 0.0
    ):
        record = {
            "timestamp": time.time(),
            "query": query,
            "experts_executed": experts,
            "evidence_count": evidence_count,
            "expanded_evidence_count": expanded_evidence_count,
            "candidate_count": candidate_count,
            "fusion_score": fusion_score,
            "agreement_score": agreement_score,
            "final_ranking": final_ranking,
            "latency": latency,
            "tokens": tokens,
            "memory_usage_mb": memory_usage_mb
        }

        # Print standard log
        logger.info(f"[EVAL-RUN] logged run for: '{query}' in {latency:.4f}s")

        # Append to file
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            logger.warning(f"Failed to write evaluation log: {e}")
