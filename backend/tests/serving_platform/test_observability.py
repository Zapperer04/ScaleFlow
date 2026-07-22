import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from backend.platform.observability.metrics import MetricsCollector
from backend.platform.observability.tracing import TelemetryTracer

def test_metrics_collection_and_prometheus_export():
    collector = MetricsCollector()
    
    # Record requests
    collector.record_request("/chat")
    collector.record_request("/chat")
    collector.record_request("/upload")
    
    # Record token usage & cost
    collector.record_tokens(100, 200, 0.05)
    
    # Record latencies
    collector.record_latency("retrieval", 0.12)
    collector.record_latency("generation", 0.45)
    
    # Export metrics
    output = collector.generate_prometheus_metrics()
    assert 'mrrag_requests_total{path="/chat"} 2' in output
    assert 'mrrag_requests_total{path="/upload"} 1' in output
    assert 'mrrag_prompt_tokens_total 100' in output
    assert 'mrrag_cost_usd_total 0.050000' in output
    assert 'mrrag_latency_seconds_avg{metric="retrieval"} 0.1200' in output

def test_telemetry_tracing():
    tracer = TelemetryTracer()
    span = tracer.start_span("retrieve_docs", "trace-id-123")
    
    with span:
        # Simulate work
        pass
