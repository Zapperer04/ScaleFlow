# DAG Builder for ScaleFlow Pipelines

TEMPLATES = {
    "document_processing_demo": {
        "name": "Document Processing Demo",
        "nodes": [
            # ── Stage 1: Pre-parse quality evaluation and enhancement ──────────
            # Evaluates blur, DPI, contrast, skew, noise, and content flags
            # (handwriting, signature, tables, image regions).
            # Applies image enhancement if quality is below thresholds.
            # Hard-rejects encrypted or corrupted PDFs before any parsing work begins.
            {
                "id": "preprocess_document",
                "task_type": "preprocess_document",
                "display_name": "Preprocess Document",
                "depends_on": [],
                "priority": "high",
                "expected_input_artifacts": [],
                "output_artifact_type": "preprocessing_report",
                "payload": {}
            },
            # ── Stage 2: Parse (uses enhanced file if preprocessing produced one) ─
            {
                "id": "parse_document",
                "task_type": "parse_document",
                "display_name": "Parse Document",
                "depends_on": ["preprocess_document"],
                "priority": "high",
                "expected_input_artifacts": ["preprocessing_report"],
                "output_artifact_type": "parsed_text",
                "payload": {}
            },
            {
                "id": "validate_parse_quality",
                "task_type": "validate_parse_quality",
                "display_name": "Validate Parse Quality",
                "depends_on": ["parse_document"],
                "priority": "high",
                "expected_input_artifacts": ["parsed_text"],
                "output_artifact_type": "parsed_text",
                "payload": {}
            },
            {
                "id": "chunk_text",
                "task_type": "chunk_text",
                "display_name": "Chunk Text",
                "depends_on": ["validate_parse_quality"],
                "priority": "medium",
                "expected_input_artifacts": ["parsed_text"],
                "output_artifact_type": "text_chunks",
                "payload": {}
            },
            {
                "id": "generate_embeddings",
                "task_type": "generate_embeddings",
                "display_name": "Generate Embeddings",
                "depends_on": ["chunk_text"],
                "priority": "medium",
                "expected_input_artifacts": ["text_chunks"],
                "output_artifact_type": "vector_index",
                "payload": {}
            },
            {
                "id": "summarize_document",
                "task_type": "summarize_document",
                "display_name": "Summarize Document",
                "depends_on": ["generate_embeddings"],
                "priority": "medium",
                "expected_input_artifacts": ["vector_index"],
                "output_artifact_type": "summary",
                "payload": {}
            }
        ]
    },
    "system_stability_pipeline": {
        "name": "System Stability Pipeline",
        "nodes": [
            {
                "id": "parse_document",
                "task_type": "parse_document",
                "display_name": "Parse Document",
                "depends_on": [],
                "priority": "high",
                "expected_input_artifacts": [],
                "output_artifact_type": "parsed_text",
                "payload": {}
            },
            {
                "id": "validate_parse_quality",
                "task_type": "validate_parse_quality",
                "display_name": "Validate Parse Quality",
                "depends_on": ["parse_document"],
                "priority": "high",
                "expected_input_artifacts": ["parsed_text"],
                "output_artifact_type": "parsed_text",
                "payload": {}
            },
            {
                "id": "chunk_text",
                "task_type": "chunk_text",
                "display_name": "Chunk Text",
                "depends_on": ["validate_parse_quality"],
                "priority": "medium",
                "expected_input_artifacts": ["parsed_text"],
                "output_artifact_type": "text_chunks",
                "payload": {}
            },
            {
                "id": "generate_embeddings",
                "task_type": "generate_embeddings",
                "display_name": "Generate Embeddings & Qdrant Insert",
                "depends_on": ["chunk_text"],
                "priority": "medium",
                "expected_input_artifacts": ["text_chunks"],
                "output_artifact_type": "vector_index",
                "payload": {}
            }
        ]
    },
    "log_analysis_demo": {
        "name": "Log Analysis Demo",
        "nodes": [
            {
                "id": "parse_logs",
                "task_type": "parse_logs",
                "display_name": "Parse Logs",
                "depends_on": [],
                "priority": "high",
                "expected_input_artifacts": [],
                "output_artifact_type": "parsed_logs",
                "payload": {}
            },
            {
                "id": "detect_error_patterns",
                "task_type": "detect_error_patterns",
                "display_name": "Detect Error Patterns",
                "depends_on": ["parse_logs"],
                "priority": "medium",
                "expected_input_artifacts": ["parsed_logs"],
                "output_artifact_type": "error_patterns",
                "payload": {}
            },
            {
                "id": "generate_embeddings",
                "task_type": "generate_embeddings",
                "display_name": "Generate Log Embeddings",
                "depends_on": ["detect_error_patterns"],
                "priority": "medium",
                "expected_input_artifacts": ["error_patterns"],
                "output_artifact_type": "vector_index",
                "payload": {}
            },
            {
                "id": "summarize_logs",
                "task_type": "summarize_logs",
                "display_name": "Summarize Logs",
                "depends_on": ["detect_error_patterns"],
                "priority": "medium",
                "expected_input_artifacts": ["error_patterns"],
                "output_artifact_type": "log_summary",
                "payload": {}
            },
            {
                "id": "final_report",
                "task_type": "final_report",
                "display_name": "Final Report Generation",
                "depends_on": ["generate_embeddings", "summarize_logs"],
                "priority": "medium",
                "expected_input_artifacts": ["vector_index", "log_summary"],
                "output_artifact_type": "final_report",
                "payload": {}
            }
        ]
    },
    "retrieval_answer_demo": {
        "name": "Retrieval Answer Demo",
        "nodes": [
            {
                "id": "embed_query",
                "task_type": "embed_query",
                "display_name": "Embed Query",
                "depends_on": [],
                "priority": "high",
                "expected_input_artifacts": [],
                "output_artifact_type": "query_vector",
                "payload": {}
            },
            {
                "id": "retrieve_context",
                "task_type": "retrieve_context",
                "display_name": "Retrieve Context",
                "depends_on": ["embed_query"],
                "priority": "medium",
                "expected_input_artifacts": ["query_vector"],
                "output_artifact_type": "retrieved_context",
                "payload": {}
            },
            {
                "id": "generate_answer_report",
                "task_type": "generate_answer_report",
                "display_name": "Generate Answer Report",
                "depends_on": ["retrieve_context"],
                "priority": "medium",
                "expected_input_artifacts": ["retrieved_context"],
                "output_artifact_type": "final_answer",
                "payload": {}
            }
        ]
    },
    "recovery_demo": {
        "name": "Lease Recovery Demo",
        "nodes": [
            {
                "id": "hang_task",
                "task_type": "send_email",
                "display_name": "Simulated Hanging Task",
                "depends_on": [],
                "priority": "medium",
                "expected_input_artifacts": [],
                "output_artifact_type": "summary",
                "payload": {
                    "to": "recovery@scaleflow.io",
                    "subject": "System Warning",
                    "body": "This task is simulated to hang to trigger lease expiration.",
                    "simulate_hang_seconds": 45
                }
            }
        ]
    },
    "replay_demo": {
        "name": "Deterministic Replay Demo",
        "nodes": [
            {
                "id": "parse_doc",
                "task_type": "parse_document",
                "display_name": "Parse Replay Document",
                "depends_on": [],
                "priority": "high",
                "expected_input_artifacts": [],
                "output_artifact_type": "parsed_text",
                "payload": {
                    "source_text": "ScaleFlow Replay Log: Step 1 initialized."
                }
            },
            {
                "id": "chunk_doc",
                "task_type": "chunk_text",
                "display_name": "Chunk Replay Text",
                "depends_on": ["parse_doc"],
                "priority": "medium",
                "expected_input_artifacts": ["parsed_text"],
                "output_artifact_type": "text_chunks",
                "payload": {}
            }
        ]
    },
    "high_load_demo": {
        "name": "High Load Backpressure Demo",
        "nodes": [
            {
                "id": "start_trigger",
                "task_type": "parse_document",
                "display_name": "Load Trigger Start",
                "depends_on": [],
                "priority": "high",
                "expected_input_artifacts": [],
                "output_artifact_type": "parsed_text",
                "payload": {
                    "source_text": "High load burst initialized."
                }
            },
            # 10 parallel tasks enqueued as soon as start_trigger finishes
            {
                "id": "burst_task_1",
                "task_type": "send_email",
                "display_name": "Burst Email Task 1",
                "depends_on": ["start_trigger"],
                "priority": "medium",
                "expected_input_artifacts": [],
                "output_artifact_type": "summary",
                "payload": {"to": "burst1@example.com", "subject": "Burst 1", "body": "High load burst task"}
            },
            {
                "id": "burst_task_2",
                "task_type": "send_email",
                "display_name": "Burst Email Task 2",
                "depends_on": ["start_trigger"],
                "priority": "medium",
                "expected_input_artifacts": [],
                "output_artifact_type": "summary",
                "payload": {"to": "burst2@example.com", "subject": "Burst 2", "body": "High load burst task"}
            },
            {
                "id": "burst_task_3",
                "task_type": "send_email",
                "display_name": "Burst Email Task 3",
                "depends_on": ["start_trigger"],
                "priority": "medium",
                "expected_input_artifacts": [],
                "output_artifact_type": "summary",
                "payload": {"to": "burst3@example.com", "subject": "Burst 3", "body": "High load burst task"}
            },
            {
                "id": "burst_task_4",
                "task_type": "send_email",
                "display_name": "Burst Email Task 4",
                "depends_on": ["start_trigger"],
                "priority": "medium",
                "expected_input_artifacts": [],
                "output_artifact_type": "summary",
                "payload": {"to": "burst4@example.com", "subject": "Burst 4", "body": "High load burst task"}
            },
            {
                "id": "burst_task_5",
                "task_type": "send_email",
                "display_name": "Burst Email Task 5",
                "depends_on": ["start_trigger"],
                "priority": "medium",
                "expected_input_artifacts": [],
                "output_artifact_type": "summary",
                "payload": {"to": "burst5@example.com", "subject": "Burst 5", "body": "High load burst task"}
            },
            {
                "id": "burst_task_6",
                "task_type": "send_email",
                "display_name": "Burst Email Task 6",
                "depends_on": ["start_trigger"],
                "priority": "medium",
                "expected_input_artifacts": [],
                "output_artifact_type": "summary",
                "payload": {"to": "burst6@example.com", "subject": "Burst 6", "body": "High load burst task"}
            },
            {
                "id": "burst_task_7",
                "task_type": "send_email",
                "display_name": "Burst Email Task 7",
                "depends_on": ["start_trigger"],
                "priority": "medium",
                "expected_input_artifacts": [],
                "output_artifact_type": "summary",
                "payload": {"to": "burst7@example.com", "subject": "Burst 7", "body": "High load burst task"}
            },
            {
                "id": "burst_task_8",
                "task_type": "send_email",
                "display_name": "Burst Email Task 8",
                "depends_on": ["start_trigger"],
                "priority": "medium",
                "expected_input_artifacts": [],
                "output_artifact_type": "summary",
                "payload": {"to": "burst8@example.com", "subject": "Burst 8", "body": "High load burst task"}
            },
            {
                "id": "burst_task_9",
                "task_type": "send_email",
                "display_name": "Burst Email Task 9",
                "depends_on": ["start_trigger"],
                "priority": "medium",
                "expected_input_artifacts": [],
                "output_artifact_type": "summary",
                "payload": {"to": "burst9@example.com", "subject": "Burst 9", "body": "High load burst task"}
            },
            {
                "id": "burst_task_10",
                "task_type": "send_email",
                "display_name": "Burst Email Task 10",
                "depends_on": ["start_trigger"],
                "priority": "medium",
                "expected_input_artifacts": [],
                "output_artifact_type": "summary",
                "payload": {"to": "burst10@example.com", "subject": "Burst 10", "body": "High load burst task"}
            }
        ]
    }
}

def get_dag_template(pipeline_type, initial_payload=None):
    """
    Returns a copy of the template with the initial payload injected
    into the root nodes (nodes with empty depends_on).
    """
    if pipeline_type not in TEMPLATES:
        raise ValueError(f"Unknown pipeline type: {pipeline_type}")
        
    template = TEMPLATES[pipeline_type]
    import copy
    dag = copy.deepcopy(template)
    
    # Inject initial payload into the first/root node(s)
    if initial_payload:
        for node in dag["nodes"]:
            if not node["depends_on"]:
                node["payload"].update(initial_payload)
                
    return dag
