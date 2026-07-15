# DAG Builder for ScaleFlow Pipelines
import copy
import logging
from collections import deque
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# Centralized constants
GRAPH_SCHEMA_VERSION = "1.0"
DEFAULT_PIPELINE_VERSION = "1.0"

# Node-level override defaults
DEFAULT_MAX_RETRIES = 3
DEFAULT_LEASE_DURATION = 600  # seconds
DEFAULT_PRIORITY = "medium"

# Global source artifacts (artifacts provided externally, not produced by nodes)
# These can be overridden in pipeline_config.
GLOBAL_SOURCE_ARTIFACTS = {"uploaded_file", "query_vector", "preprocessing_report"}


# -----------------------------------------------------------------------------
# Pipeline templates with global config and versioning
# -----------------------------------------------------------------------------
def _make_template(template_name: str, display_name: str, nodes: List[Dict],
                   version: str = DEFAULT_PIPELINE_VERSION,
                   pipeline_config: Optional[Dict] = None) -> Dict:
    """
    Factory for pipeline templates with global config and schema version.
    """
    if pipeline_config is None:
        pipeline_config = {
            "graph_enabled": True,
            "graph_schema_version": GRAPH_SCHEMA_VERSION,
            "parser_version": "1.0",
            "embedding_enabled": True,
            "bm25_enabled": True,
            "source_artifacts": GLOBAL_SOURCE_ARTIFACTS,
        }
    else:
        # Ensure source_artifacts is present
        pipeline_config.setdefault("source_artifacts", GLOBAL_SOURCE_ARTIFACTS)

    return {
        "name": template_name,
        "display_name": display_name,
        "version": version,
        "schema_version": GRAPH_SCHEMA_VERSION,
        "created_at": None,  # Will be set at instantiation time
        "pipeline_config": pipeline_config,
        "nodes": nodes
    }


TEMPLATES = {
    "document_processing_demo": _make_template(
        "document_processing_demo",
        "Document Processing Demo",
        [
            # ── Stage 1: Preprocessing ──
            {
                "id": "preprocess_document",
                "task_type": "preprocess_document",
                "display_name": "Preprocess Document (VLM‑ready)",
                "depends_on": [],
                "priority": "high",
                "expected_input_artifacts": ["uploaded_file"],
                "output_artifact_type": "preprocessing_report",
                "payload": {}
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
                "payload": {}
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
                "payload": {}
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
                "payload": {}
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
                "payload": {}
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
                "payload": {}
            },
            # ── Stage 6: BM25 Index (parallel to embeddings) ──
            {
                "id": "build_bm25_index",
                "task_type": "build_bm25_index",
                "display_name": "Build BM25 Index",
                "depends_on": ["chunk_text"],
                "priority": "medium",
                "expected_input_artifacts": ["graph_chunks"],
                "output_artifact_type": "bm25_index",
                "payload": {}
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
                "payload": {}
            }
        ],
        pipeline_config={
            "graph_enabled": True,
            "graph_schema_version": GRAPH_SCHEMA_VERSION,
            "parser_version": "1.0",
            "embedding_enabled": True,
            "bm25_enabled": True,
        }
    ),
    "retrieval_answer_demo": _make_template(
        "retrieval_answer_demo",
        "Retrieval Answer Demo",
        [
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
                "payload": {}
            },
            {
                "id": "expand_graph_context",
                "task_type": "expand_graph_context",
                "display_name": "Expand Graph Context",
                "depends_on": ["retrieve_context"],
                "priority": "medium",
                "expected_input_artifacts": ["retrieved_context"],
                "output_artifact_type": "expanded_context",
                "payload": {}
            },
            {
                "id": "rerank_context",
                "task_type": "rerank_context",
                "display_name": "Rerank Context",
                "depends_on": ["expand_graph_context"],
                "priority": "medium",
                "expected_input_artifacts": ["expanded_context"],
                "output_artifact_type": "reranked_context",
                "payload": {}
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
        ],
        pipeline_config={
            "graph_enabled": True,
            "embedding_enabled": True,
            "bm25_enabled": True,
        }
    ),
    "test_small_pipeline": _make_template(
        "test_small_pipeline",
        "Test Small Pipeline",
        [
            {
                "id": "task_a",
                "task_type": "generate_report",
                "display_name": "Task A",
                "depends_on": [],
                "priority": "medium",
                "expected_input_artifacts": [],
                "output_artifact_type": "report_pdf",
                "payload": {"report_type": "test_report"}
            },
            {
                "id": "task_b",
                "task_type": "send_email",
                "display_name": "Task B",
                "depends_on": ["task_a"],
                "priority": "medium",
                "expected_input_artifacts": ["report_pdf"],
                "output_artifact_type": "email_notification",
                "payload": {"to": "test@example.com"}
            }
        ]
    ),
    "test_parallel_pipeline": _make_template(
        "test_parallel_pipeline",
        "Test Parallel Pipeline",
        [
            {
                "id": "task_a",
                "task_type": "generate_report",
                "display_name": "Task A",
                "depends_on": [],
                "priority": "medium",
                "expected_input_artifacts": [],
                "output_artifact_type": "report_pdf",
                "payload": {"report_type": "test_report"}
            },
            {
                "id": "task_b",
                "task_type": "send_email",
                "display_name": "Task B",
                "depends_on": ["task_a"],
                "priority": "medium",
                "expected_input_artifacts": ["report_pdf"],
                "output_artifact_type": "email_notification_b",
                "payload": {"to": "b@example.com"}
            },
            {
                "id": "task_c",
                "task_type": "send_email",
                "display_name": "Task C",
                "depends_on": ["task_a"],
                "priority": "medium",
                "expected_input_artifacts": ["report_pdf"],
                "output_artifact_type": "email_notification_c",
                "payload": {"to": "c@example.com"}
            },
            {
                "id": "task_d",
                "task_type": "process_video",
                "display_name": "Task D",
                "depends_on": ["task_b", "task_c"],
                "priority": "medium",
                "expected_input_artifacts": ["email_notification_b", "email_notification_c"],
                "output_artifact_type": "video_result",
                "payload": {"file": "video.mp4"}
            }
        ]
    )
}


# -----------------------------------------------------------------------------
# DAG Validation Utilities
# -----------------------------------------------------------------------------
def validate_dag(dag: Dict) -> None:
    """
    Validate DAG structure:
    - Unique node IDs
    - All dependencies point to existing nodes
    - No cycles (topological sort)
    - At least one root node (no dependencies)
    - No orphan nodes (all reachable from roots)
    - Artifact compatibility: each node's expected_input_artifacts must be
      provided by some ancestor (direct or indirect), or be in source_artifacts.
    """
    nodes = dag.get("nodes", [])
    if not nodes:
        raise ValueError("DAG has no nodes.")

    node_ids = {n["id"] for n in nodes}
    if len(node_ids) != len(nodes):
        raise ValueError("Duplicate node IDs found.")

    # Build adjacency and dependency maps
    adj = {nid: [] for nid in node_ids}
    rev_adj = {nid: [] for nid in node_ids}
    node_map = {n["id"]: n for n in nodes}
    node_outputs = {n["id"]: n.get("output_artifact_type") for n in nodes}
    node_inputs = {n["id"]: n.get("expected_input_artifacts", []) for n in nodes}

    for n in nodes:
        nid = n["id"]
        for dep in n.get("depends_on", []):
            if dep not in node_ids:
                raise ValueError(f"Node '{nid}' depends on unknown node '{dep}'.")
            adj[dep].append(nid)
            rev_adj[nid].append(dep)

    # Detect cycles via Kahn's algorithm (topological sort)
    in_degree = {nid: len(rev_adj[nid]) for nid in node_ids}
    queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
    topo_order = []

    while queue:
        curr = queue.popleft()
        topo_order.append(curr)
        for child in adj[curr]:
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

    if len(topo_order) != len(node_ids):
        cycle_nodes = set(node_ids) - set(topo_order)
        raise ValueError(f"Cycle detected in DAG involving nodes: {cycle_nodes}")

    # Check root exists
    roots = [nid for nid, deg in {nid: len(rev_adj[nid]) for nid in node_ids}.items() if deg == 0]
    if not roots:
        raise ValueError("DAG has no root node (no node with empty depends_on).")

    # Check orphan nodes (unreachable from roots)
    reachable = set()
    stack = list(roots)
    while stack:
        nid = stack.pop()
        if nid not in reachable:
            reachable.add(nid)
            stack.extend(adj[nid])
    orphans = node_ids - reachable
    if orphans:
        raise ValueError(f"Orphan nodes (unreachable from roots): {orphans}")

    # Artifact compatibility validation (transitive)
    # Get source artifacts from pipeline config
    pipeline_config = dag.get("pipeline_config", {})
    source_artifacts = set(pipeline_config.get("source_artifacts", GLOBAL_SOURCE_ARTIFACTS))

    # For each node, compute all artifacts produced by ancestors (including direct and indirect)
    # We'll do a BFS from each node up the dependency chain.
    for nid, n in node_map.items():
        required = set(n.get("expected_input_artifacts", []))
        if not required:
            continue
        # Collect all ancestors' outputs
        ancestor_outputs = set()
        stack = list(n.get("depends_on", []))
        while stack:
            dep_id = stack.pop()
            if dep_id not in node_map:
                continue
            dep_node = node_map[dep_id]
            # Add output of this dependency
            output = dep_node.get("output_artifact_type")
            if output:
                ancestor_outputs.add(output)
            # Add its dependencies (for transitive)
            stack.extend(dep_node.get("depends_on", []))
        # The required artifacts must be in ancestor_outputs or source_artifacts
        missing = required - (ancestor_outputs | source_artifacts)
        if missing:
            raise ValueError(
                f"Node '{nid}' expects artifact(s) {missing} not produced by any ancestor and not in source artifacts. "
                f"Ancestor outputs: {ancestor_outputs}, Source artifacts: {source_artifacts}"
            )


# -----------------------------------------------------------------------------
# Main API
# -----------------------------------------------------------------------------
def get_dag_template(pipeline_type: str, initial_payload: Optional[Dict] = None,
                     node_overrides: Optional[Dict] = None,
                     pipeline_config_override: Optional[Dict] = None) -> Dict:
    """
    Returns a validated, instantiated DAG copy with:
      - Pipeline-level config merged with overrides
      - Node-level overrides for retries, priority, lease, etc.
      - Schema version and pipeline version injected
      - Topological sort order preserved (already validated)
    """
    if pipeline_type not in TEMPLATES:
        raise ValueError(f"Unknown pipeline type: {pipeline_type}")

    template = TEMPLATES[pipeline_type]
    dag = copy.deepcopy(template)

    # Merge pipeline config overrides
    if pipeline_config_override:
        dag["pipeline_config"].update(pipeline_config_override)

    # Inject initial payload into root nodes (those with empty depends_on)
    if initial_payload:
        for node in dag["nodes"]:
            if not node.get("depends_on"):
                node["payload"].update(initial_payload)

    # Apply node-level overrides (e.g., max_retries, priority, lease_seconds)
    if node_overrides:
        for node in dag["nodes"]:
            nid = node["id"]
            if nid in node_overrides:
                over = node_overrides[nid]
                if "max_retries" in over:
                    node["max_retries"] = over["max_retries"]
                if "priority" in over:
                    node["priority"] = over["priority"]
                if "lease_seconds" in over:
                    node["lease_seconds"] = over["lease_seconds"]
                # Any other fields can be added

    # Inject default retry/lease/priority if not present
    for node in dag["nodes"]:
        if "max_retries" not in node:
            node["max_retries"] = DEFAULT_MAX_RETRIES
        if "lease_seconds" not in node:
            node["lease_seconds"] = DEFAULT_LEASE_DURATION
        if "priority" not in node:
            node["priority"] = DEFAULT_PRIORITY

    # Validate the DAG
    validate_dag(dag)

    # Add timestamp and version info
    from datetime import datetime
    dag["created_at"] = datetime.utcnow().isoformat() + "Z"

    return dag

# -----------------------------------------------------------------------------
# Utility to list available templates
# -----------------------------------------------------------------------------
def list_templates() -> List[str]:
    return list(TEMPLATES.keys())