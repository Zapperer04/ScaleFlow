from dataclasses import dataclass
from typing import Dict, Any
from backend.domain.value_objects.chunk_id import ChunkId
from backend.domain.value_objects.embedding_vector import EmbeddingVector

@dataclass(frozen=True)
class Embedding:
    chunk_id: ChunkId
    embedding_vector: EmbeddingVector
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id.to_dict(),
            "embedding_vector": self.embedding_vector.to_dict(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Embedding":
        return cls(
            chunk_id=ChunkId.from_dict(data["chunk_id"]),
            embedding_vector=EmbeddingVector.from_dict(data["embedding_vector"]),
            metadata=data.get("metadata", {}),
        )
