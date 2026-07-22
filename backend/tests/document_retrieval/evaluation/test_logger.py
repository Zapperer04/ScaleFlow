import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from engine.document_retrieval.evaluation.retrieval_logger import RetrievalLogger

def test_logger_writing(tmp_path):
    log_dir = str(tmp_path)
    logger_instance = RetrievalLogger(log_dir=log_dir)
    
    logger_instance.log_run(
        query="What is OAuth?",
        experts=["vector", "graph"],
        evidence_count=2,
        expanded_evidence_count=4,
        candidate_count=2,
        fusion_score=0.95,
        agreement_score=2.0,
        final_ranking=["chunk-0"],
        latency=0.08,
        tokens=150
    )
    
    assert os.path.exists(logger_instance.log_path)
    with open(logger_instance.log_path, "r") as f:
        lines = f.readlines()
        assert len(lines) == 1
