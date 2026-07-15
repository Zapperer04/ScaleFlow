# Central Task Type Registry and Payload Validation for ScaleFlow
import re
import importlib
import logging
from typing import Dict, Any, Optional, Callable, List, Union

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------
# Multiplier to compute lease duration from estimated runtime
LEASE_MULTIPLIER = 3.0  # lease = estimated_runtime * LEASE_MULTIPLIER

# Email validation regex
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

# ------------------------------------------------------------------------------
# Consolidated Task Registry (Single Source of Truth)
# ------------------------------------------------------------------------------
# Each entry defines:
#   - handler_name: string (can be a dotted path to a function)
#   - capability: logical group for queue routing (must exist in CAPABILITY_QUEUES)
#   - retry_policy: dict with max_retries, retry_delay_seconds
#   - estimated_runtime_seconds: used for lease duration calculation
#   - required_fields: list of required payload fields
#   - optional_fields: list of optional payload fields
#   - frontend_fields: for UI rendering (not used for validation)
#   - description: human-readable description
#   - label: short display name
#   - lease_override (optional): explicit lease duration in seconds
#   - validation_rules (optional): dict mapping field names to validation rules
#
# Handlers are lazy-loaded via get_handler().

TASK_REGISTRY: Dict[str, Dict[str, Any]] = {
    "test_isolated_task": {
        "label": "Test Isolated Task",
        "description": "Used for recovery and isolation testing.",
        "required_fields": ["to", "subject", "body"],
        "optional_fields": ["simulate_hang_seconds"],
        "retry_policy": {"max_retries": 3, "retry_delay_seconds": 5},
        "estimated_runtime_seconds": 3,
        "handler_name": "worker.handle_send_email",
        "capability": "default"
    },
    "send_email": {
        "label": "Email Delivery",
        "description": "Simulates sending an email notification.",
        "required_fields": ["to", "subject", "body"],
        "optional_fields": ["cc", "simulate_hang_seconds"],
        "frontend_fields": [
            {"name": "to", "label": "Recipient Email", "type": "email", "placeholder": "user@example.com"},
            {"name": "subject", "label": "Subject", "type": "text", "placeholder": "Welcome"},
            {"name": "body", "label": "Body", "type": "textarea", "placeholder": "Message body"},
            {"name": "cc", "label": "CC Email", "type": "email", "placeholder": "copy@example.com"},
            {"name": "simulate_hang_seconds", "label": "Simulate Hang (Seconds)", "type": "number", "placeholder": "e.g. 45"}
        ],
        "retry_policy": {"max_retries": 3, "retry_delay_seconds": 5},
        "estimated_runtime_seconds": 3,
        "handler_name": "worker.handle_send_email",
        "capability": "io_heavy",
        "validation_rules": {
            "to": {"type": "email"},
            "simulate_hang_seconds": {"type": "int", "min": 0, "max": 3600}
        }
    },
    "process_video": {
        "label": "Video Processing",
        "description": "Transcodes video to requested format and resolution.",
        "required_fields": ["file"],
        "optional_fields": ["format", "resolution", "simulate_hang_seconds"],
        "frontend_fields": [
            {"name": "file", "label": "Video File Path", "type": "text", "placeholder": "media/video_1080p.mp4"},
            {"name": "format", "label": "Output Format", "type": "text", "placeholder": "mp4"},
            {"name": "resolution", "label": "Resolution", "type": "text", "placeholder": "720p"},
            {"name": "simulate_hang_seconds", "label": "Simulate Hang (Seconds)", "type": "number", "placeholder": "e.g. 45"}
        ],
        "retry_policy": {"max_retries": 2, "retry_delay_seconds": 10},
        "estimated_runtime_seconds": 5,
        "handler_name": "worker.handle_process_video",
        "capability": "cpu_heavy",
        "validation_rules": {
            "simulate_hang_seconds": {"type": "int", "min": 0, "max": 3600}
        }
    },
    "generate_report": {
        "label": "Generate Report",
        "description": "Compiles statistical report data.",
        "required_fields": ["report_type"],
        "optional_fields": ["format", "simulate_hang_seconds"],
        "frontend_fields": [
            {"name": "report_type", "label": "Report Type", "type": "text", "placeholder": "Monthly Sales Report"},
            {"name": "format", "label": "Output Format", "type": "text", "placeholder": "PDF"},
            {"name": "simulate_hang_seconds", "label": "Simulate Hang (Seconds)", "type": "number", "placeholder": "e.g. 45"}
        ],
        "retry_policy": {"max_retries": 4, "retry_delay_seconds": 8},
        "estimated_runtime_seconds": 4,
        "handler_name": "worker.handle_generate_report",
        "capability": "cpu_heavy",
        "validation_rules": {
            "simulate_hang_seconds": {"type": "int", "min": 0, "max": 3600}
        }
    },
    "preprocess_document": {
        "label": "Preprocess Document",
        "description": "Assesses document quality and performs image enhancement before VLM parsing.",
        "required_fields": [],
        "optional_fields": ["simulate_hang_seconds", "graph_schema_version"],
        "frontend_fields": [],
        "retry_policy": {"max_retries": 2, "retry_delay_seconds": 10},
        "estimated_runtime_seconds": 60,
        "handler_name": "worker.handle_preprocess_document",
        "capability": "cpu_heavy",
        "lease_override": 180,  # explicit lease
        "validation_rules": {
            "simulate_hang_seconds": {"type": "int", "min": 0, "max": 3600}
        }
    },
    "parse_document": {
        "label": "Parse Document",
        "description": "Parses documents using VLM-first parsing and produces a document graph.",
        "required_fields": [],
        "optional_fields": ["source_text", "simulate_hang_seconds", "graph_schema_version", "graph_node_count", "graph_edge_count", "graph_depth", "graph_enabled"],
        "frontend_fields": [
            {"name": "source_text", "label": "Source Text", "type": "textarea", "placeholder": "Input document content..."}
        ],
        "retry_policy": {"max_retries": 3, "retry_delay_seconds": 5},
        "estimated_runtime_seconds": 300,
        "handler_name": "worker.handle_parse_document",
        "capability": "cpu_heavy",
        "lease_override": 600,
        "validation_rules": {
            "simulate_hang_seconds": {"type": "int", "min": 0, "max": 3600},
            "graph_node_count": {"type": "int", "min": 0},
            "graph_edge_count": {"type": "int", "min": 0},
            "graph_depth": {"type": "int", "min": 0},
            "graph_enabled": {"type": "bool"}
        }
    },
    "persist_document_graph": {
        "label": "Persist Document Graph",
        "description": "Stores the extracted document graph for recovery and later analysis.",
        "required_fields": [],
        "optional_fields": ["simulate_hang_seconds", "graph_schema_version", "graph_node_count", "graph_edge_count"],
        "frontend_fields": [],
        "retry_policy": {"max_retries": 2, "retry_delay_seconds": 5},
        "estimated_runtime_seconds": 30,
        "handler_name": "worker.handle_persist_document_graph",
        "capability": "io_heavy",
        "validation_rules": {
            "simulate_hang_seconds": {"type": "int", "min": 0, "max": 3600},
            "graph_node_count": {"type": "int", "min": 0},
            "graph_edge_count": {"type": "int", "min": 0}
        }
    },
    "validate_parse_quality": {
        "label": "Validate Parse Quality",
        "description": "Validates document graph quality, OCR fallback quality, and graph extraction metrics.",
        "required_fields": [],
        "optional_fields": ["simulate_hang_seconds", "graph_schema_version"],
        "frontend_fields": [],
        "retry_policy": {"max_retries": 3, "retry_delay_seconds": 5},
        "estimated_runtime_seconds": 30,
        "handler_name": "worker.handle_validate_parse_quality",
        "capability": "cpu_heavy",
        "validation_rules": {
            "simulate_hang_seconds": {"type": "int", "min": 0, "max": 3600}
        }
    },
    "chunk_text": {
        "label": "Chunk Text",
        "description": "Transforms document graphs into semantic graph chunks.",
        "required_fields": [],
        "optional_fields": ["simulate_hang_seconds", "graph_schema_version", "graph_node_count", "graph_edge_count", "graph_depth", "graph_enabled"],
        "frontend_fields": [],
        "retry_policy": {"max_retries": 3, "retry_delay_seconds": 5},
        "estimated_runtime_seconds": 120,
        "handler_name": "worker.handle_chunk_text",
        "capability": "cpu_heavy",
        "validation_rules": {
            "simulate_hang_seconds": {"type": "int", "min": 0, "max": 3600},
            "graph_node_count": {"type": "int", "min": 0},
            "graph_edge_count": {"type": "int", "min": 0},
            "graph_depth": {"type": "int", "min": 0},
            "graph_enabled": {"type": "bool"}
        }
    },
    "generate_embeddings": {
        "label": "Generate Embeddings",
        "description": "Generates graph-aware semantic embeddings for graph chunks.",
        "required_fields": [],
        "optional_fields": ["simulate_hang_seconds", "graph_schema_version"],
        "frontend_fields": [],
        "retry_policy": {"max_retries": 3, "retry_delay_seconds": 5},
        "estimated_runtime_seconds": 600,
        "handler_name": "worker.handle_generate_embeddings",
        "capability": "embedding_gpu",
        "lease_override": 900,
        "validation_rules": {
            "simulate_hang_seconds": {"type": "int", "min": 0, "max": 3600}
        }
    },
    "build_bm25_index": {
        "label": "Build BM25 Index",
        "description": "Constructs a BM25 index from the chunked text for hybrid retrieval.",
        "required_fields": [],
        "optional_fields": ["simulate_hang_seconds", "graph_schema_version"],
        "frontend_fields": [],
        "retry_policy": {"max_retries": 2, "retry_delay_seconds": 10},
        "estimated_runtime_seconds": 180,
        "handler_name": "worker.handle_build_bm25_index",
        "capability": "retrieval_optimized",
        "validation_rules": {
            "simulate_hang_seconds": {"type": "int", "min": 0, "max": 3600}
        }
    },
    "summarize_document": {
        "label": "Summarize Document",
        "description": "Summarizes processed document chunks.",
        "required_fields": [],
        "optional_fields": ["simulate_hang_seconds"],
        "frontend_fields": [],
        "retry_policy": {"max_retries": 3, "retry_delay_seconds": 5},
        "estimated_runtime_seconds": 2,
        "handler_name": "worker.handle_summarize_document",
        "capability": "summarization_llm",
        "validation_rules": {
            "simulate_hang_seconds": {"type": "int", "min": 0, "max": 3600}
        }
    },
    "parse_logs": {
        "label": "Parse Logs",
        "description": "Parses input logs for errors.",
        "required_fields": [],
        "optional_fields": ["source_text", "simulate_hang_seconds"],
        "frontend_fields": [
            {"name": "source_text", "label": "Logs Text", "type": "textarea", "placeholder": "Input logs content..."}
        ],
        "retry_policy": {"max_retries": 3, "retry_delay_seconds": 5},
        "estimated_runtime_seconds": 2,
        "handler_name": "worker.handle_parse_logs",
        "capability": "cpu_heavy",
        "validation_rules": {
            "simulate_hang_seconds": {"type": "int", "min": 0, "max": 3600}
        }
    },
    "detect_error_patterns": {
        "label": "Detect Error Patterns",
        "description": "Detects specific patterns or keywords in logs.",
        "required_fields": [],
        "optional_fields": ["simulate_hang_seconds"],
        "frontend_fields": [],
        "retry_policy": {"max_retries": 3, "retry_delay_seconds": 5},
        "estimated_runtime_seconds": 2,
        "handler_name": "worker.handle_detect_error_patterns",
        "capability": "cpu_heavy",
        "validation_rules": {
            "simulate_hang_seconds": {"type": "int", "min": 0, "max": 3600}
        }
    },
    "summarize_logs": {
        "label": "Summarize Logs",
        "description": "Summarizes the error patterns.",
        "required_fields": [],
        "optional_fields": ["simulate_hang_seconds"],
        "frontend_fields": [],
        "retry_policy": {"max_retries": 3, "retry_delay_seconds": 5},
        "estimated_runtime_seconds": 2,
        "handler_name": "worker.handle_summarize_logs",
        "capability": "summarization_llm",
        "validation_rules": {
            "simulate_hang_seconds": {"type": "int", "min": 0, "max": 3600}
        }
    },
    "final_report": {
        "label": "Final Report",
        "description": "Generates a final log analysis report.",
        "required_fields": [],
        "optional_fields": ["simulate_hang_seconds"],
        "frontend_fields": [],
        "retry_policy": {"max_retries": 3, "retry_delay_seconds": 5},
        "estimated_runtime_seconds": 3,
        "handler_name": "worker.handle_final_report",
        "capability": "cpu_heavy",
        "validation_rules": {
            "simulate_hang_seconds": {"type": "int", "min": 0, "max": 3600}
        }
    },
    "embed_query": {
        "label": "Embed Query",
        "description": "Generates query embedding vector.",
        "required_fields": ["query"],
        "optional_fields": ["top_k", "pipeline_id_filter", "file_id_filter", "simulate_hang_seconds"],
        "frontend_fields": [
            {"name": "query", "label": "Query Text", "type": "textarea", "placeholder": "Search query..."}
        ],
        "retry_policy": {"max_retries": 3, "retry_delay_seconds": 5},
        "estimated_runtime_seconds": 2,
        "handler_name": "worker.handle_embed_query",
        "capability": "embedding_gpu",
        "validation_rules": {
            "top_k": {"type": "int", "min": 1, "max": 100},
            "pipeline_id_filter": {"type": "int", "min": 0},
            "file_id_filter": {"type": "int", "min": 0},
            "simulate_hang_seconds": {"type": "int", "min": 0, "max": 3600}
        }
    },
    "retrieve_context": {
        "label": "Retrieve Context",
        "description": "Performs hybrid retrieval using dense search, BM25 search, graph expansion, and reranking.",
        "required_fields": [],
        "optional_fields": ["simulate_hang_seconds", "graph_schema_version"],
        "frontend_fields": [],
        "retry_policy": {"max_retries": 3, "retry_delay_seconds": 5},
        "estimated_runtime_seconds": 60,
        "handler_name": "worker.handle_retrieve_context",
        "capability": "retrieval_optimized",
        "validation_rules": {
            "simulate_hang_seconds": {"type": "int", "min": 0, "max": 3600}
        }
    },
    "expand_graph_context": {
        "label": "Expand Graph Context",
        "description": "Expands context by traversing the chunk graph to fetch related neighbours.",
        "required_fields": [],
        "optional_fields": ["simulate_hang_seconds", "graph_schema_version"],
        "frontend_fields": [],
        "retry_policy": {"max_retries": 2, "retry_delay_seconds": 5},
        "estimated_runtime_seconds": 60,
        "handler_name": "worker.handle_expand_graph_context",
        "capability": "retrieval_optimized",
        "validation_rules": {
            "simulate_hang_seconds": {"type": "int", "min": 0, "max": 3600}
        }
    },
    "rerank_context": {
        "label": "Rerank Context",
        "description": "Reranks retrieved chunks using a cross‑encoder for final relevance.",
        "required_fields": [],
        "optional_fields": ["simulate_hang_seconds", "graph_schema_version"],
        "frontend_fields": [],
        "retry_policy": {"max_retries": 2, "retry_delay_seconds": 5},
        "estimated_runtime_seconds": 120,
        "handler_name": "worker.handle_rerank_context",
        "capability": "retrieval_optimized",
        "validation_rules": {
            "simulate_hang_seconds": {"type": "int", "min": 0, "max": 3600}
        }
    },
    "generate_answer_report": {
        "label": "Generate Answer Report",
        "description": "Generates grounded answers from graph retrieval context.",
        "required_fields": [],
        "optional_fields": ["simulate_hang_seconds"],
        "frontend_fields": [],
        "retry_policy": {"max_retries": 3, "retry_delay_seconds": 5},
        "estimated_runtime_seconds": 120,
        "handler_name": "worker.handle_generate_answer_report",
        "capability": "summarization_llm",
        "validation_rules": {
            "simulate_hang_seconds": {"type": "int", "min": 0, "max": 3600}
        }
    }
}

# ------------------------------------------------------------------------------
# Capability to queue mapping (derived from registry)
# ------------------------------------------------------------------------------
CAPABILITY_QUEUES = {
    "test_isolated": "task_queue_test_isolated",
    "io_heavy": "task_queue_io_heavy",
    "cpu_heavy": "task_queue_cpu_heavy",
    "embedding_gpu": "task_queue_embedding_gpu",
    "retrieval_optimized": "task_queue_retrieval_optimized",
    "summarization_llm": "task_queue_summarization_llm",
    "default": "task_queue_default",
}

# Verify that all capabilities used in registry are defined
for task_name, info in TASK_REGISTRY.items():
    cap = info.get("capability", "default")
    if cap not in CAPABILITY_QUEUES:
        raise ValueError(f"Task '{task_name}' uses unknown capability '{cap}'. Must be one of {list(CAPABILITY_QUEUES.keys())}")

# ------------------------------------------------------------------------------
# Handler loading (lazy)
# ------------------------------------------------------------------------------
_handler_cache: Dict[str, Callable] = {}
_handler_failure_cache: set = set()  # track failed handlers to avoid repeated import attempts

def get_handler(task_type: str) -> Callable:
    """Return a callable handler for a task type, loading it from the registry."""
    if task_type not in TASK_REGISTRY:
        raise ValueError(f"Unknown task type: {task_type}")
    if task_type in _handler_failure_cache:
        raise ImportError(f"Handler for '{task_type}' previously failed to load.")
    if task_type in _handler_cache:
        return _handler_cache[task_type]
    info = TASK_REGISTRY[task_type]
    handler_path = info.get("handler_name")
    if not handler_path:
        raise ValueError(f"Task '{task_type}' has no handler defined.")
    module_path, func_name = handler_path.rsplit('.', 1)
    try:
        module = importlib.import_module(module_path)
        func = getattr(module, func_name)
    except (ImportError, AttributeError) as e:
        _handler_failure_cache.add(task_type)
        raise ImportError(f"Failed to load handler for '{task_type}': {e}") from e
    _handler_cache[task_type] = func
    return func

# ------------------------------------------------------------------------------
# Payload Validation
# ------------------------------------------------------------------------------
def _validate_field(value: Any, rule: Dict[str, Any]) -> bool:
    """Validate a single field against a rule dict."""
    val_type = rule.get("type")
    if val_type == "email":
        return isinstance(value, str) and EMAIL_REGEX.match(value)
    elif val_type == "int":
        if not isinstance(value, int):
            return False
        if "min" in rule and value < rule["min"]:
            return False
        if "max" in rule and value > rule["max"]:
            return False
        return True
    elif val_type == "float":
        if not isinstance(value, (int, float)):
            return False
        if "min" in rule and value < rule["min"]:
            return False
        if "max" in rule and value > rule["max"]:
            return False
        return True
    elif val_type == "bool":
        return isinstance(value, bool)
    elif val_type == "str":
        return isinstance(value, str)
    elif val_type == "list":
        return isinstance(value, list)
    elif val_type == "dict":
        return isinstance(value, dict)
    # Unknown type, assume valid
    return True

def validate_task_payload(task_type: str, payload: Dict[str, Any], strict: bool = True) -> tuple[bool, Optional[str]]:
    """
    Validates a task payload against the registry.
    Returns (is_valid, error_message).
    If strict=True, unknown fields are rejected.
    """
    if not task_type:
        return False, "Task type is required"
    if task_type not in TASK_REGISTRY:
        return False, f"Unsupported task type: {task_type}"

    info = TASK_REGISTRY[task_type]
    required = info.get("required_fields", [])
    optional = info.get("optional_fields", [])
    known_fields = set(required) | set(optional)
    validation_rules = info.get("validation_rules", {})

    # Check required fields
    for field in required:
        if field not in payload or payload.get(field) is None or str(payload[field]).strip() == "":
            return False, f"Missing required field: {field}"

    # Validate each field against rules
    for field, val in payload.items():
        if field not in known_fields:
            if strict:
                return False, f"Unknown field: {field}"
            continue
        if field in validation_rules:
            rule = validation_rules[field]
            if not _validate_field(val, rule):
                return False, f"Invalid value for field '{field}' (rule: {rule})"

    return True, None

# ------------------------------------------------------------------------------
# Task utility functions
# ------------------------------------------------------------------------------
def get_task_capability(task_type: str) -> str:
    return TASK_REGISTRY.get(task_type, {}).get("capability", "default")

def get_queue_name(task_type: str, priority: Any, is_test: bool = False) -> str:
    priority_val = getattr(priority, 'value', priority)
    cap = get_task_capability(task_type)
    base_queue = CAPABILITY_QUEUES.get(cap, CAPABILITY_QUEUES["default"])
    # Standardize capability queue suffix logic
    if is_test:
        if base_queue.startswith("task_queue_test_"):
            return f"{base_queue}_{priority_val}"
        elif base_queue.startswith("task_queue_"):
            return f"task_queue_test_{base_queue[11:]}_{priority_val}"
        return f"test_{base_queue}_{priority_val}"
    return f"{base_queue}_{priority_val}"

def get_task_lease_duration(task_type: str) -> int:
    """Return lease duration in seconds, using lease_override if present, else computed."""
    info = TASK_REGISTRY.get(task_type, {})
    if "lease_override" in info:
        return info["lease_override"]
    estimated = info.get("estimated_runtime_seconds", 60)
    return int(estimated * LEASE_MULTIPLIER)

def get_retry_policy(task_type: str) -> Dict[str, Any]:
    return TASK_REGISTRY.get(task_type, {}).get("retry_policy", {"max_retries": 3, "retry_delay_seconds": 5})

# ------------------------------------------------------------------------------
# Startup validation
# ------------------------------------------------------------------------------
def validate_registry() -> None:
    """
    Called at startup to verify all handlers are loadable and all capabilities exist.
    This function must be called during application initialization.
    """
    errors = []
    for task_name, info in TASK_REGISTRY.items():
        # Verify handler exists
        try:
            get_handler(task_name)
        except Exception as e:
            errors.append(f"Handler for '{task_name}' failed to load: {e}")
        # Verify capability
        cap = info.get("capability")
        if cap not in CAPABILITY_QUEUES:
            errors.append(f"Task '{task_name}' uses unknown capability '{cap}'")
        # Ensure lease duration is positive
        if get_task_lease_duration(task_name) <= 0:
            errors.append(f"Task '{task_name}' has non-positive lease duration")
    if errors:
        raise RuntimeError("Task registry validation failed:\n" + "\n".join(errors))
    logger.info("Task registry validation passed.")

# ------------------------------------------------------------------------------
# Module initialization (call validate_registry on import if desired)
# ------------------------------------------------------------------------------
# Uncomment the following line to auto-validate on import.
# However, for production, it's better to explicitly call it in your main startup.
# validate_registry()

CAPABILITY_MAPPINGS = {
    task_name: info.get("capability", "default")
    for task_name, info in TASK_REGISTRY.items()
}