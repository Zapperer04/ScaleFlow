from dataclasses import dataclass
from typing import Dict, Any, Optional
from backend.domain.value_objects.chunk_id import ChunkId
from backend.domain.value_objects.page_number import PageNumber

@dataclass(frozen=True)
class Chunk:
    chunk_id: ChunkId
    chunk_index: int
    chunk_text: str
    page_number: PageNumber
    file_id: int
    pipeline_id: int
    metadata: Dict[str, Any]
    graph_relations: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id.to_dict(),
            "chunk_index": self.chunk_index,
            "chunk_text": self.chunk_text,
            "page_number": self.page_number.to_dict(),
            "file_id": self.file_id,
            "pipeline_id": self.pipeline_id,
            "metadata": self.metadata,
            "graph_relations": self.graph_relations,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Chunk":
        return cls(
            chunk_id=ChunkId.from_dict(data["chunk_id"]),
            chunk_index=int(data["chunk_index"]),
            chunk_text=str(data["chunk_text"]),
            page_number=PageNumber.from_dict(data["page_number"]),
            file_id=int(data["file_id"]),
            pipeline_id=int(data["pipeline_id"]),
            metadata=data.get("metadata", {}),
            graph_relations=data.get("graph_relations"),
        )
