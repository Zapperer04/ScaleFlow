import os
import uuid
import time
import logging
import json
import psutil
from logging.handlers import RotatingFileHandler
from typing import Dict, Any, Optional

# Setup directories for logging
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Rotating log handlers
logger = logging.getLogger("ScaleFlowObservability")
logger.setLevel(logging.INFO)

# JSON format formatter
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "filename": record.filename,
            "line": record.lineno
        }
        if hasattr(record, "trace_id"):
            log_data["trace_id"] = record.trace_id
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id
        if hasattr(record, "metrics"):
            log_data["metrics"] = record.metrics
        return json.dumps(log_data)

json_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, "scaleflow.json"),
    maxBytes=5 * 1024 * 1024,
    backupCount=5
)
json_handler.setFormatter(JsonFormatter())
logger.addHandler(json_handler)

# Simple in-memory trace store for evaluation / dashboard inspections
traces_store: Dict[str, Dict[str, Any]] = {}

def get_memory_usage_mb() -> float:
    """Returns current process memory utilization in MB"""
    try:
        process = psutil.Process(os.getpid())
        return round(process.memory_info().rss / (1024 * 1024), 2)
    except:
        return 0.0

def start_trace(query: str, correlation_id: Optional[str] = None, request_id: Optional[str] = None) -> Dict[str, Any]:
    """Starts a new trace, returning the trace metadata dictionary"""
    trace_id = f"tr-{uuid.uuid4().hex[:12]}"
    corr_id = correlation_id or f"corr-{uuid.uuid4().hex[:12]}"
    req_id = request_id or f"req-{uuid.uuid4().hex[:12]}"
    
    trace_data = {
        "trace_id": trace_id,
        "correlation_id": corr_id,
        "request_id": req_id,
        "query": query,
        "start_time": time.time(),
        "memory_start_mb": get_memory_usage_mb(),
        "stages": {},
        "metrics": {
            "token_counts": {"input": 0, "output": 0, "total": 0},
            "retrieval_counts": {"chunks": 0, "nodes": 0},
            "cache": {"hits": 0, "misses": 0},
            "errors": 0,
            "warnings": 0
        },
        "llm_meta": {},
        "status": "active"
    }
    
    traces_store[trace_id] = trace_data
    
    # Log to rotated JSON logs
    extra = {"trace_id": trace_id, "correlation_id": corr_id}
    logger.info(f"Trace started for query: {query}", extra=extra)
    
    return trace_data

def log_stage(trace_id: str, stage_name: str, duration_ms: float, metadata: Optional[Dict[str, Any]] = None) -> None:
    """Logs the completion of a pipeline stage (retrieval, reranking, fusion, llm)"""
    if trace_id not in traces_store:
        return
        
    trace = traces_store[trace_id]
    trace["stages"][stage_name] = {
        "duration_ms": round(duration_ms, 2),
        "timestamp": time.time(),
        "metadata": metadata or {}
    }
    
    # Keep query logs updated
    extra = {
        "trace_id": trace_id, 
        "correlation_id": trace["correlation_id"],
        "metrics": {"stage": stage_name, "duration_ms": duration_ms}
    }
    logger.info(f"Stage '{stage_name}' completed in {duration_ms:.2f}ms", extra=extra)

def finalize_trace(trace_id: str, answer: str, final_status: str = "success", error_msg: Optional[str] = None) -> Dict[str, Any]:
    """Finalizes a trace, recording latency, outputs, and memory stats"""
    if trace_id not in traces_store:
        return {}
        
    trace = traces_store[trace_id]
    trace["status"] = final_status
    trace["end_time"] = time.time()
    trace["latency_ms"] = round((trace["end_time"] - trace["start_time"]) * 1000, 2)
    trace["memory_end_mb"] = get_memory_usage_mb()
    trace["memory_delta_mb"] = round(trace["memory_end_mb"] - trace["memory_start_mb"], 2)
    trace["answer"] = answer
    
    if error_msg:
        trace["error_message"] = error_msg
        trace["metrics"]["errors"] += 1
        
    extra = {
        "trace_id": trace_id,
        "correlation_id": trace["correlation_id"],
        "metrics": {
            "total_latency_ms": trace["latency_ms"],
            "memory_delta_mb": trace["memory_delta_mb"]
        }
    }
    logger.info(f"Trace finalized with status '{final_status}' in {trace['latency_ms']:.2f}ms", extra=extra)
    return trace

def increment_metric(trace_id: str, category: str, subkey: str, amount: int = 1) -> None:
    """Increments telemetry counter metrics (e.g. cache hits/misses, tokens)"""
    if trace_id not in traces_store:
        return
    trace = traces_store[trace_id]
    if category in trace["metrics"] and subkey in trace["metrics"][category]:
        trace["metrics"][category][subkey] += amount
        if category == "token_counts" and subkey in ("input", "output"):
            trace["metrics"]["token_counts"]["total"] = (
                trace["metrics"]["token_counts"]["input"] + trace["metrics"]["token_counts"]["output"]
            )

def get_trace(trace_id: str) -> Optional[Dict[str, Any]]:
    return traces_store.get(trace_id)

def get_all_traces() -> Dict[str, Dict[str, Any]]:
    return traces_store
