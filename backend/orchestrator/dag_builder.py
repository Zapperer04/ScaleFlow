# DAG Builder for ScaleFlow Pipelines

TEMPLATES = {
    "document_processing_demo": {
        "name": "Document Processing Demo",
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
                "id": "chunk_text",
                "task_type": "chunk_text",
                "display_name": "Chunk Text",
                "depends_on": ["parse_document"],
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
