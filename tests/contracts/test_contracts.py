import os
import json
import pytest
from jsonschema import validate

EXPECTED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "expected"))

def get_golden_docs():
    if not os.path.exists(EXPECTED_DIR):
        return []
    return [d for d in os.listdir(EXPECTED_DIR) if os.path.isdir(os.path.join(EXPECTED_DIR, d))]

# Define formal JSON Schemas
METADATA_SCHEMA = {
    "type": "object",
    "properties": {
        "chunk_count": {"type": "integer"},
        "document_type": {"type": "string"},
        "embedding_count": {"type": "integer"},
        "parser_used": {"type": "string"},
        "quality_score": {"type": "number"}
    },
    "required": ["document_type", "quality_score"]
}

PARSER_SCHEMA = {
    "type": "object",
    "properties": {
        "pages": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "page_number": {"type": "integer"},
                    "text": {"type": "string"},
                    "nodes": {"type": "array"}
                },
                "required": ["page_number"]
            }
        }
    }
}

CHUNK_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "metadata": {
                "type": "object",
                "properties": {
                    "chunk_id": {"type": "string"},
                    "document_id": {"type": "string"}
                },
                "required": ["chunk_id"]
            }
        },
        "required": ["text", "metadata"]
    }
}

GRAPH_SCHEMA = {
    "type": "object",
    "properties": {
        "nodes": {"type": "array"},
        "edges": {"type": "array"}
    }
}

@pytest.mark.contracts
def test_metadata_schema_contract():
    for doc in get_golden_docs():
        meta_path = os.path.join(EXPECTED_DIR, doc, "metadata.json")
        if os.path.exists(meta_path):
            with open(meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            validate(instance=data, schema=METADATA_SCHEMA)

@pytest.mark.contracts
def test_parser_schema_contract():
    for doc in get_golden_docs():
        parser_path = os.path.join(EXPECTED_DIR, doc, "parser_output.json")
        if os.path.exists(parser_path):
            with open(parser_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # If the parser output is a dictionary (graph or text pages), validate schema
            if isinstance(data, dict):
                validate(instance=data, schema=PARSER_SCHEMA)

@pytest.mark.contracts
def test_chunks_schema_contract():
    for doc in get_golden_docs():
        chunks_path = os.path.join(EXPECTED_DIR, doc, "chunks.json")
        if os.path.exists(chunks_path):
            with open(chunks_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            validate(instance=data, schema=CHUNK_SCHEMA)

@pytest.mark.contracts
def test_graph_schema_contract():
    for doc in get_golden_docs():
        graph_path = os.path.join(EXPECTED_DIR, doc, "document_graph.json")
        if os.path.exists(graph_path):
            with open(graph_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "nodes" in data or "edges" in data:
                validate(instance=data, schema=GRAPH_SCHEMA)
