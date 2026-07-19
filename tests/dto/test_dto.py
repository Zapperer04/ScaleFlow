import pytest
from backend.dto.chunking import ChunkDTO

def test_dto_immutability():
    dto = ChunkDTO(
        chunk_id="chunk_1",
        chunk_index=0,
        chunk_text="Test text",
        page_number=1,
        file_id=10,
        pipeline_id=20,
    )
    with pytest.raises(Exception):
        dto.chunk_id = "chunk_2"  # Should be immutable

def test_dto_serialization():
    dto = ChunkDTO(
        chunk_id="chunk_1",
        chunk_index=0,
        chunk_text="Test text",
        page_number=1,
        file_id=10,
        pipeline_id=20,
    )
    data = dto.model_dump()
    assert data["chunk_id"] == "chunk_1"
    assert data["version"] == "v1"
    assert data["schema_version"] == 1
    assert "created_at" in data
