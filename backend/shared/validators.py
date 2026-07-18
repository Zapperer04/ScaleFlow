from typing import Dict, Any, List
from backend.domain.exceptions.exceptions import ValidationError, InvalidGraph, InvalidChunk, InvalidEmbedding, InvalidMetadata, InvalidTransition
from backend.domain.states import PipelineState, validate_transition

def validate_graph_structure(data: Dict[str, Any]) -> None:
    if not isinstance(data, dict):
        raise InvalidGraph("Graph data must be a dictionary")
    if "nodes" not in data or "edges" not in data:
        raise InvalidGraph("Graph must contain both 'nodes' and 'edges'")
    if not isinstance(data["nodes"], list) or not isinstance(data["edges"], list):
        raise InvalidGraph("'nodes' and 'edges' must be lists")
    for n in data["nodes"]:
        if not isinstance(n, dict) or "node_id" not in n or "label" not in n:
            raise InvalidGraph("Each node must contain 'node_id' and 'label'")
    for e in data["edges"]:
        if not isinstance(e, dict) or "source" not in e or "target" not in e or "relation" not in e:
            raise InvalidGraph("Each edge must contain 'source', 'target', and 'relation'")

def validate_chunk_data(data: Dict[str, Any]) -> None:
    required = ["chunk_id", "chunk_index", "chunk_text", "page_number", "file_id", "pipeline_id"]
    for field in required:
        if field not in data:
            raise InvalidChunk(f"Chunk is missing required field: {field}")
    if not isinstance(data["chunk_id"], str) or not data["chunk_id"].strip():
        raise InvalidChunk("chunk_id must be a non-empty string")
    if not isinstance(data["chunk_index"], int) or data["chunk_index"] < 0:
        raise InvalidChunk("chunk_index must be a non-negative integer")

def validate_embedding_data(data: Dict[str, Any]) -> None:
    if "chunk_id" not in data or "embedding_vector" not in data:
        raise InvalidEmbedding("Embedding must contain 'chunk_id' and 'embedding_vector'")
    if not isinstance(data["embedding_vector"], list) or not all(isinstance(x, (int, float)) for x in data["embedding_vector"]):
        raise InvalidEmbedding("embedding_vector must be a list of floats")

def validate_metadata_data(data: Dict[str, Any]) -> None:
    if not isinstance(data, dict):
        raise InvalidMetadata("Metadata must be a dictionary")
    # Custom project metadata rules can go here

def validate_pipeline_state_transition(current: str, target: str) -> None:
    try:
        curr_state = PipelineState(current)
        targ_state = PipelineState(target)
        validate_transition(curr_state, targ_state)
    except ValueError as e:
        raise InvalidTransition(f"Invalid state value: {e}")
