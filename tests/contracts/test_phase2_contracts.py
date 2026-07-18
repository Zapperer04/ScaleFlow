import os
import json
import pytest
from jsonschema import validate

SCHEMAS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend", "contracts", "schemas", "v1"))

def get_schema(name: str) -> dict:
    filepath = os.path.join(SCHEMAS_DIR, name)
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.mark.contracts
def test_generated_schemas_exist():
    expected = [
        "ParserResponse.json",
        "Chunk.json",
        "Graph.json",
        "Node.json",
        "Edge.json",
        "Metadata.json",
        "Embedding.json",
        "RetrievalRequest.json",
        "RetrievalResponse.json",
        "PipelineState.json"
    ]
    for name in expected:
        assert os.path.exists(os.path.join(SCHEMAS_DIR, name))

@pytest.mark.contracts
def test_chunk_schema_validation():
    schema = get_schema("Chunk.json")
    valid_instance = {
        "chunk_id": "c_123",
        "chunk_index": 1,
        "chunk_text": "Sample content",
        "page_number": 2,
        "file_id": 101,
        "pipeline_id": 202,
        "metadata": {},
        "version": "v1",
        "schema_version": 1,
        "created_at": "2026-07-18T12:00:00Z"
    }
    validate(instance=valid_instance, schema=schema)
