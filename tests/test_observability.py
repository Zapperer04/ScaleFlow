import pytest
from backend.observability import start_trace, log_stage, increment_metric, finalize_trace, get_trace

def test_telemetry_trace_flow():
    trace = start_trace("How does forecasting work?")
    trace_id = trace["trace_id"]
    
    assert trace["query"] == "How does forecasting work?"
    assert trace["status"] == "active"
    
    # Log stage completions
    log_stage(trace_id, "retrieval", 250.0, {"nodes_found": 5})
    log_stage(trace_id, "llm_generation", 800.0)
    
    # Increment metrics
    increment_metric(trace_id, "token_counts", "input", 150)
    increment_metric(trace_id, "token_counts", "output", 80)
    increment_metric(trace_id, "cache", "hits", 2)
    
    # Finalize
    final_trace = finalize_trace(trace_id, "Forecasting relies on history models.")
    
    assert final_trace["status"] == "success"
    assert final_trace["latency_ms"] > 0
    assert final_trace["answer"] == "Forecasting relies on history models."
    
    # Verify values saved in store
    saved = get_trace(trace_id)
    assert saved["metrics"]["token_counts"]["total"] == 230
    assert saved["metrics"]["cache"]["hits"] == 2
    assert "retrieval" in saved["stages"]
    assert saved["stages"]["retrieval"]["duration_ms"] == 250.0
