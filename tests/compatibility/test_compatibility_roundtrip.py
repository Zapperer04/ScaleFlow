import pytest
from backend.adapters.chunk_adapter import ChunkAdapter
from backend.adapters.graph_adapter import GraphAdapter
from backend.adapters.embedding_adapter import EmbeddingAdapter
from backend.adapters.retrieval_adapter import RetrievalAdapter
from backend.adapters.parser_adapter import ParserAdapter
from backend.adapters.pipeline_adapter import PipelineAdapter

def test_chunk_compatibility_roundtrip():
    legacy = {
        "chunk_id": "chunk_abc",
        "chunk_index": 5,
        "chunk_text": "Compatibility text details",
        "page_number": 12,
        "file_id": 99,
        "pipeline_id": 88,
        "metadata": {"section": "appendix"},
        "graph_relations": None
    }
    # Roundtrip Legacy -> Domain -> Legacy
    domain = ChunkAdapter.legacy_to_domain(legacy)
    round_legacy = ChunkAdapter.domain_to_legacy(domain)
    # Check match (note that value objects serialize to primitives)
    assert round_legacy["chunk_id"] == legacy["chunk_id"]
    assert round_legacy["chunk_index"] == legacy["chunk_index"]
    assert round_legacy["chunk_text"] == legacy["chunk_text"]
    assert round_legacy["page_number"] == legacy["page_number"]
    assert round_legacy["file_id"] == legacy["file_id"]
    assert round_legacy["pipeline_id"] == legacy["pipeline_id"]
    assert round_legacy["metadata"] == legacy["metadata"]

    # Roundtrip Legacy -> DTO -> Legacy
    dto = ChunkAdapter.legacy_to_dto(legacy)
    round_legacy_dto = ChunkAdapter.dto_to_legacy(dto)
    assert round_legacy_dto["chunk_id"] == legacy["chunk_id"]
    assert round_legacy_dto["chunk_index"] == legacy["chunk_index"]
    assert round_legacy_dto["chunk_text"] == legacy["chunk_text"]
    assert round_legacy_dto["page_number"] == legacy["page_number"]
    assert round_legacy_dto["file_id"] == legacy["file_id"]
    assert round_legacy_dto["pipeline_id"] == legacy["pipeline_id"]
    assert round_legacy_dto["metadata"] == legacy["metadata"]

def test_graph_compatibility_roundtrip():
    legacy = {
        "nodes": [
            {"node_id": "n1", "label": "Entity", "properties": {"name": "A"}}
        ],
        "edges": [
            {"source": "n1", "target": "n1", "relation": "self", "properties": {}}
        ]
    }
    domain = GraphAdapter.legacy_to_domain(legacy)
    round_legacy = GraphAdapter.domain_to_legacy(domain)
    assert round_legacy["nodes"][0]["node_id"] == "n1"
    assert round_legacy["edges"][0]["source"] == "n1"

    dto = GraphAdapter.legacy_to_dto(legacy)
    round_legacy_dto = GraphAdapter.dto_to_legacy(dto)
    assert round_legacy_dto["nodes"][0]["node_id"] == "n1"
