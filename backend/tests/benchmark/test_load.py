import pytest
import time
import os
import sys

# Ensure backend directory is in path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

def calculate_percentiles(latencies):
    if not latencies:
        return 0.0, 0.0, 0.0
    sorted_latencies = sorted(latencies)
    n = len(sorted_latencies)
    p50 = sorted_latencies[int(n * 0.5)]
    p95 = sorted_latencies[int(n * 0.95)] if n > 1 else sorted_latencies[0]
    p99 = sorted_latencies[int(n * 0.99)] if n > 1 else sorted_latencies[0]
    return p50, p95, p99

def test_load_percentiles_calculation():
    latencies = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    p50, p95, p99 = calculate_percentiles(latencies)
    assert p50 == 0.6
    assert p95 == 1.0
    assert p99 == 1.0
