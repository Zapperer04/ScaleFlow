from typing import Dict, Any
from backend.domain.entities.chunk import Chunk
from backend.domain.value_objects.chunk_id import ChunkId
from backend.domain.value_objects.page_number import PageNumber
from backend.dto.chunking import ChunkDTO

class ChunkAdapter:
    @staticmethod
    def legacy_to_domain(legacy_dict: Dict[str, Any]) -> Chunk:
        return Chunk(
            chunk_id=ChunkId(str(legacy_dict["chunk_id"])),
            chunk_index=int(legacy_dict.get("chunk_index", 0)),
            chunk_text=str(legacy_dict.get("chunk_text", "")),
            page_number=PageNumber(int(legacy_dict.get("page_number", 0))),
            file_id=int(legacy_dict.get("file_id", 0)),
            pipeline_id=int(legacy_dict.get("pipeline_id", 0)),
            metadata=legacy_dict.get("metadata", {}),
            graph_relations=legacy_dict.get("graph_relations"),
        )

    @staticmethod
    def domain_to_legacy(domain_chunk: Chunk) -> Dict[str, Any]:
        return domain_chunk.to_dict()

    @staticmethod
    def legacy_to_dto(legacy_dict: Dict[str, Any]) -> ChunkDTO:
        return ChunkDTO(
            chunk_id=str(legacy_dict["chunk_id"]),
            chunk_index=int(legacy_dict.get("chunk_index", 0)),
            chunk_text=str(legacy_dict.get("chunk_text", "")),
            page_number=int(legacy_dict.get("page_number", 0)),
            file_id=int(legacy_dict.get("file_id", 0)),
            pipeline_id=int(legacy_dict.get("pipeline_id", 0)),
            metadata=legacy_dict.get("metadata", {}),
            graph_relations=legacy_dict.get("graph_relations"),
        )

    @staticmethod
    def dto_to_legacy(dto: ChunkDTO) -> Dict[str, Any]:
        return dto.model_dump()
