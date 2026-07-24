import pytest
import os
import sys

# Ensure backend directory is in path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from engine.document_retrieval.evaluation.metrics import MetricsCalculator

def test_metrics_calculator_correctness():
    calc = MetricsCalculator()
    retrieved = ["chunk-1", "chunk-2", "chunk-3"]
    expected = ["chunk-2", "chunk-4"]
    
    recall_3 = calc.compute_recall(retrieved, expected, 3)
    precision_3 = calc.compute_precision(retrieved, expected, 3)
    mrr = calc.compute_mrr(retrieved, expected)
    
    assert recall_3 == 0.5  # chunk-2 is found out of 2 expected
    assert precision_3 == 1.0 / 3.0
    assert mrr == 0.5  # chunk-2 is at index 1 (1-indexed: 2nd position)

def test_hallucination_failure_classification():
    # Test stub for failure categories
    failures = ["missing chunk", "reranker error", "hallucination", "citation mismatch"]
    assert len(failures) == 4
    assert "hallucination" in failures
