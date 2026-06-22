# DAG Builder for ScaleFlow Pipelines
import copy

TEMPLATES = {
    "document_processing_demo": {
        "name": "Document Processing Demo",
        "nodes": [
            # ── Dynamic Enhancement Node Placement Target ──
            {
                "id": "enhance_document",
                "task_type": "enhance_document",
                "display_name": "Cloud VLM Document Enhancement",
                "depends_on": [],
                "priority": "high",
                "expected_input_artifacts": ["uploaded_file"],
                "output_artifact_type": "enhanced_text",
                "payload": {}
            },
            # ── Stage 2: Parse ──
            {
                "id": "parse_document",
                "task_type": "parse_document",
                "display_name": "Parse Document",
                "depends_on": [],
                "priority": "high",
                "expected_input_artifacts": ["preprocessing_report", "uploaded_file"],
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
                "expected_input_artifacts": [["parsed_text", "enhanced_text"]],
                "output_artifact_type": "text_chunks",
                "payload": {}
            },
            {
                "id": "generate_embeddings",
                "task_type": "generate_embeddings",
                "display_name": "Generate Quantum Embeddings",
                "depends_on": ["chunk_text"],
                "priority": "medium",
                "expected_input_artifacts": ["text_chunks"],
                "output_artifact_type": "vector_index",
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
                "display_name": "Generate Answer",
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
    dag = copy.deepcopy(template)
    
    # Inject initial payload into the first/root node(s)
    if initial_payload:
        for node in dag["nodes"]:
            if not node["depends_on"]:
                node["payload"].update(initial_payload)
                
    return dag