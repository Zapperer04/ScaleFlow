import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from services.document_retrieval.evaluation.metrics import MetricsCalculator

def test_metrics_calculations():
    calculator = MetricsCalculator()
    
    retrieved = ["chunk-0", "chunk-1", "chunk-2"]
    expected = ["chunk-0", "chunk-2"]
    
    scores = calculator.calculate_all(
        retrieved_chunks=retrieved,
        expected_chunks=expected,
        retrieved_nodes=[],
        expected_nodes=[],
        retrieved_entities=[],
        expected_entities=[],
        retrieved_tables=[],
        expected_tables=[]
    )
    
    # Verify values
    assert scores["recall_5"] == 1.0
    assert scores["precision_1"] == 1.0
    assert scores["mrr"] == 1.0
    assert scores["ndcg_5"] > 0.0
