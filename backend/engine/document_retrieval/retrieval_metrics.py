import time
import logging
import json
import os
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class RetrievalMetricsCollector:
    def __init__(self, log_path: str = None):
        if log_path is None:
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            log_path = os.path.join(current_dir, "storage", "document_store", "retrieval_metrics.jsonl")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        self.log_path = log_path

    def log_metrics(
        self,
        query: str,
        expert_latencies: Dict[str, float],
        fusion_latency: float,
        rerank_latency: float,
        optimizer_latency: float,
        total_latency: float,
        candidate_count: int,
        evidence_count: int,
        agreement_count: int,
        final_token_count: int,
        confidence_distribution: Dict[str, float]
    ):
        metrics_record = {
            "timestamp": time.time(),
            "query": query,
            "expert_latencies": expert_latencies,
            "fusion_latency": fusion_latency,
            "rerank_latency": rerank_latency,
            "optimizer_latency": optimizer_latency,
            "total_latency": total_latency,
            "candidate_count": candidate_count,
            "evidence_count": evidence_count,
            "agreement_count": agreement_count,
            "final_token_count": final_token_count,
            "confidence_distribution": confidence_distribution
        }

        # Log to Python standard log
        logger.info(f"[METRICS] Retrieval completed in {total_latency:.4f}s. final_token_count={final_token_count}")

        # Append to JSONL file
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(metrics_record) + "\n")
        except Exception as e:
            logger.warning(f"Failed to write retrieval metrics to file: {e}")
