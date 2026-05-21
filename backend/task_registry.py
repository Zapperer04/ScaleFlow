# Central Task Type Registry and Payload Validation for ScaleFlow

TASK_REGISTRY = {
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
