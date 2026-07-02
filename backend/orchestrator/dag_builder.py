# DAG Builder for ScaleFlow Pipelines
import copy

TEMPLATES = {
    "document_processing_demo": {
        "name": "Document Processing Demo",
        "nodes": [
            # ── Stage 1: Preprocessing ──
            {
                "id": "preprocess_document",
                "task_type": "preprocess_document",
                "display_name": "Preprocess Document (VLM‑ready)",
                "depends_on": [],
                "priority": "high",
                "expected_input_artifacts": ["uploaded_file"],
                "output_artifact_type": "preprocessing_report",
                "payload": {
                    "graph_enabled": True,
                    "graph_schema_version": "1.0"
                }
            },
            # ── Stage 2: VLM Parsing → Document Graph ──
            {
                "id": "parse_document",
                "task_type": "parse_document",
                "display_name": "Parse Document (VLM‑first)",
                "depends_on": ["preprocess_document"],
                "priority": "high",
                "expected_input_artifacts": ["preprocessing_report", "uploaded_file"],
                "output_artifact_type": "document_graph",
                "payload": {
                    "graph_enabled": True,
                    "graph_schema_version": "1.0"
                }
            },
            # ── Stage 2b: Persist graph for recovery ──
            {
                "id": "persist_document_graph",
                "task_type": "persist_document_graph",
                "display_name": "Persist Document Graph",
                "depends_on": ["parse_document"],
                "priority": "high",
                "expected_input_artifacts": ["document_graph"],
                "output_artifact_type": "document_graph",
                "payload": {
                    "graph_enabled": True,
                    "graph_schema_version": "1.0"
                }
            },
            # ── Stage 3: Quality Gate ──
            {
                "id": "validate_parse_quality",
                "task_type": "validate_parse_quality",
                "display_name": "Validate Graph Quality",
                "depends_on": ["persist_document_graph"],
                "priority": "high",
                "expected_input_artifacts": ["document_graph"],
                "output_artifact_type": "document_graph",
                "payload": {
                    "graph_enabled": True
                }
            },
            # ── Stage 4: Semantic Chunking ──
            {
                "id": "chunk_text",
                "task_type": "chunk_text",
                "display_name": "Chunk Text (Graph‑native)",
                "depends_on": ["validate_parse_quality"],
                "priority": "medium",
                "expected_input_artifacts": ["document_graph"],
                "output_artifact_type": "graph_chunks",
                "payload": {
                    "graph_enabled": True
                }
            },
            # ── Stage 5: Graph Embeddings ──
            {
                "id": "generate_embeddings",
                "task_type": "generate_embeddings",
                "display_name": "Generate Graph Embeddings",
                "depends_on": ["chunk_text"],
                "priority": "medium",
                "expected_input_artifacts": ["graph_chunks"],
                "output_artifact_type": "graph_embeddings",
                "payload": {
                    "graph_enabled": True
                }
            },
            # ── Stage 6: BM25 Index (parallel to embeddings) ──
            {
                "id": "build_bm25_index",
                "task_type": "build_bm25_index",
                "display_name": "Build BM25 Index",
                "depends_on": ["chunk_text"],   # only needs chunks, not embeddings
                "priority": "medium",
                "expected_input_artifacts": ["graph_chunks"],
                "output_artifact_type": "bm25_index",
                "payload": {
                    "graph_enabled": True
                }
            },
            # ── Stage 7: Summarisation (depends on both embeddings and BM25) ──
            {
                "id": "summarize_document",
                "task_type": "summarize_document",
                "display_name": "Summarize Document",
                "depends_on": ["generate_embeddings", "build_bm25_index"],
                "priority": "low",
                "expected_input_artifacts": ["graph_chunks"],
                "output_artifact_type": "summary",
                "payload": {
                    "graph_enabled": True
                }
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
                "display_name": "Retrieve Context (Hybrid)",
                "depends_on": ["embed_query"],
                "priority": "medium",
                "expected_input_artifacts": ["query_vector"],
                "output_artifact_type": "retrieved_context",
                "payload": {
                    "graph_enabled": True
                }
            },
            {
                "id": "expand_graph_context",
                "task_type": "expand_graph_context",
                "display_name": "Expand Graph Context",
                "depends_on": ["retrieve_context"],
                "priority": "medium",
                "expected_input_artifacts": ["retrieved_context"],
                "output_artifact_type": "expanded_context",
                "payload": {
                    "graph_enabled": True
                }
            },
            {
                "id": "rerank_context",
                "task_type": "rerank_context",
                "display_name": "Rerank Context",
                "depends_on": ["expand_graph_context"],
                "priority": "medium",
                "expected_input_artifacts": ["expanded_context"],
                "output_artifact_type": "reranked_context",
                "payload": {
                    "graph_enabled": True
                }
            },
            {
                "id": "generate_answer_report",
                "task_type": "generate_answer_report",
                "display_name": "Generate Answer",
                "depends_on": ["rerank_context"],
                "priority": "medium",
                "expected_input_artifacts": ["reranked_context"],
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