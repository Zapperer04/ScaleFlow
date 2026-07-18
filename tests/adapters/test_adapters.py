from backend.adapters.chunk_adapter import ChunkAdapter

def test_chunk_adapter_roundtrip():
    legacy_chunk = {
        "chunk_id": "c1",
        "chunk_index": 2,
        "chunk_text": "Sample text",
        "page_number": 3,
        "file_id": 4,
        "pipeline_id": 5,
        "metadata": {"author": "John"},
        "graph_relations": None,
    }

    # Legacy -> Domain
    domain_chunk = ChunkAdapter.legacy_to_domain(legacy_chunk)
    assert domain_chunk.chunk_id.value == "c1"
    assert domain_chunk.page_number.value == 3

    # Domain -> Legacy
    round_legacy = ChunkAdapter.domain_to_legacy(domain_chunk)
    # The serialization of page_number and chunk_id will map to primitives
    assert round_legacy["chunk_id"] == "c1"
    assert round_legacy["page_number"] == 3

    # Legacy -> DTO
    dto_chunk = ChunkAdapter.legacy_to_dto(legacy_chunk)
    assert dto_chunk.chunk_id == "c1"

    # DTO -> Legacy
    round_legacy_dto = ChunkAdapter.dto_to_legacy(dto_chunk)
    assert round_legacy_dto["chunk_id"] == "c1"
