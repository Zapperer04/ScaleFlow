# Central Task Type Registry and Payload Validation for ScaleFlow

TASK_REGISTRY = {
    "test_isolated_task": {
        "label": "Isolated Test Task",
        "description": "Used for isolated integration tests.",
        "required_fields": [],
        "optional_fields": ["to", "subject", "body", "simulate_hang_seconds"],
        "retry_policy": {"max_retries": 3, "retry_delay_seconds": 5},
        "estimated_runtime_seconds": 1,
        "handler_name": "handle_test_isolated"
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
        "handler_name": "handle_send_email"
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
        "handler_name": "handle_process_video"
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
        "handler_name": "handle_generate_report"
    },
    "parse_document": {
        "label": "Parse Document",
        "description": "Normalizes document text.",
        "required_fields": [],
        "optional_fields": ["source_text", "simulate_hang_seconds"],
        "frontend_fields": [
            {"name": "source_text", "label": "Source Text", "type": "textarea", "placeholder": "Input document content..."}
        ],
        "retry_policy": {"max_retries": 3, "retry_delay_seconds": 5},
        "estimated_runtime_seconds": 2,
        "handler_name": "handle_parse_document"
    },
    "chunk_text": {
        "label": "Chunk Text",
        "description": "Splits text into chunks.",
        "required_fields": [],
        "optional_fields": ["simulate_hang_seconds"],
        "frontend_fields": [],
        "retry_policy": {"max_retries": 3, "retry_delay_seconds": 5},
        "estimated_runtime_seconds": 2,
        "handler_name": "handle_chunk_text"
    },
    "generate_embeddings": {
        "label": "Generate Embeddings",
        "description": "Generates mock embedding vectors.",
        "required_fields": [],
        "optional_fields": ["simulate_hang_seconds"],
        "frontend_fields": [],
        "retry_policy": {"max_retries": 3, "retry_delay_seconds": 5},
        "estimated_runtime_seconds": 3,
        "handler_name": "handle_generate_embeddings"
    },
    "summarize_document": {
        "label": "Summarize Document",
        "description": "Summarizes processed document chunks.",
        "required_fields": [],
        "optional_fields": ["simulate_hang_seconds"],
        "frontend_fields": [],
        "retry_policy": {"max_retries": 3, "retry_delay_seconds": 5},
        "estimated_runtime_seconds": 2,
        "handler_name": "handle_summarize_document"
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
        "handler_name": "handle_parse_logs"
    },
    "detect_error_patterns": {
        "label": "Detect Error Patterns",
        "description": "Detects specific patterns or keywords in logs.",
        "required_fields": [],
        "optional_fields": ["simulate_hang_seconds"],
        "frontend_fields": [],
        "retry_policy": {"max_retries": 3, "retry_delay_seconds": 5},
        "estimated_runtime_seconds": 2,
        "handler_name": "handle_detect_error_patterns"
    },
    "summarize_logs": {
        "label": "Summarize Logs",
        "description": "Summarizes the error patterns.",
        "required_fields": [],
        "optional_fields": ["simulate_hang_seconds"],
        "frontend_fields": [],
        "retry_policy": {"max_retries": 3, "retry_delay_seconds": 5},
        "estimated_runtime_seconds": 2,
        "handler_name": "handle_summarize_logs"
    },
    "final_report": {
        "label": "Final Report",
        "description": "Generates a final log analysis report.",
        "required_fields": [],
        "optional_fields": ["simulate_hang_seconds"],
        "frontend_fields": [],
        "retry_policy": {"max_retries": 3, "retry_delay_seconds": 5},
        "estimated_runtime_seconds": 3,
        "handler_name": "handle_final_report"
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
        "handler_name": "handle_embed_query"
    },
    "retrieve_context": {
        "label": "Retrieve Context",
        "description": "Retrieves semantic match context from Qdrant.",
        "required_fields": [],
        "optional_fields": ["simulate_hang_seconds"],
        "frontend_fields": [],
        "retry_policy": {"max_retries": 3, "retry_delay_seconds": 5},
        "estimated_runtime_seconds": 3,
        "handler_name": "handle_retrieve_context"
    },
    "generate_answer_report": {
        "label": "Generate Answer Report",
        "description": "Compiles retrieved context chunks into a final extractive report.",
        "required_fields": [],
        "optional_fields": ["simulate_hang_seconds"],
        "frontend_fields": [],
        "retry_policy": {"max_retries": 3, "retry_delay_seconds": 5},
        "estimated_runtime_seconds": 2,
        "handler_name": "handle_generate_answer_report"
    }
}

def validate_task_payload(task_type, payload):
    if not task_type:
        return False, "Task type is required"
    if task_type not in TASK_REGISTRY:
        return False, f"Unsupported task type: {task_type}"
    
    registry_info = TASK_REGISTRY[task_type]
    required_fields = registry_info.get("required_fields", [])
    frontend_fields = registry_info.get("frontend_fields", [])
    fields_schema = {f["name"]: f for f in frontend_fields}
    
    # 1. Verify all required fields are present
    for field in required_fields:
        if field not in payload:
            return False, f"Missing required field: {field}"
            
    # 2. Validate all provided fields
    for field_name, val in payload.items():
        if field_name not in fields_schema:
            # Skip validation for non-schema fields, or reject them.
            # We'll allow them for flexibility but skip checks.
            continue
            
        field_def = fields_schema[field_name]
        field_type = field_def.get("type")
        
        # Clean up whitespace
        str_val = str(val).strip() if val is not None else ""
        
        # If it's a required field, or if it was provided, validate that it is not empty
        if field_name in required_fields:
            if not str_val:
                return False, f"Missing required field: {field_name}"
        else:
            # Optional field was provided, check if it's empty
            if val is not None and not str_val:
                return False, f"Field '{field_name}' cannot be empty if provided"
                
        # Value-specific validation
        if str_val:
            if field_type == "email":
                if "@" not in str_val:
                    return False, f"Invalid email field: {field_name}"
                    
    return True, None

CAPABILITY_MAPPINGS = {
    "test_isolated_task": "test_isolated",
    "send_email": "io_heavy",
    "process_video": "cpu_heavy",
    "generate_report": "cpu_heavy",
    "parse_document": "cpu_heavy",
    "chunk_text": "cpu_heavy",
    "generate_embeddings": "embedding_gpu",
    "summarize_document": "summarization_llm",
    "parse_logs": "cpu_heavy",
    "detect_error_patterns": "cpu_heavy",
    "summarize_logs": "summarization_llm",
    "final_report": "cpu_heavy",
    "embed_query": "embedding_gpu",
    "retrieve_context": "retrieval_optimized",
    "generate_answer_report": "summarization_llm"
}

def get_task_capability(task_type):
    return CAPABILITY_MAPPINGS.get(task_type, "default")

def get_queue_name(task_type, priority, is_test=False):
    cap = get_task_capability(task_type)
    if is_test:
        return f"task_queue_test_{cap}_{priority}"
    return f"task_queue_{cap}_{priority}"
