from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from backend.domain.value_objects.document_id import DocumentId
from backend.domain.entities.page import Page
from backend.domain.entities.chunk import Chunk
from backend.domain.entities.graph import Graph
from backend.domain.entities.artifact import Artifact

@dataclass(frozen=True)
class Document:
    document_id: DocumentId
    filename: str
    pages: List[Page] = field(default_factory=list)
    chunks: List[Chunk] = field(default_factory=list)
    graph: Optional[Graph] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    artifacts: List[Artifact] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id.to_dict(),
            "filename": self.filename,
            "pages": [p.to_dict() for p in self.pages],
            "chunks": [c.to_dict() for c in self.chunks],
            "graph": self.graph.to_dict() if self.graph else None,
            "metadata": self.metadata,
            "artifacts": [a.to_dict() for a in self.artifacts],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Document":
        return cls(
            document_id=DocumentId.from_dict(data["document_id"]),
            filename=str(data["filename"]),
            pages=[Page.from_dict(p) for p in data.get("pages", [])],
            chunks=[Chunk.from_dict(c) for c in data.get("chunks", [])],
            graph=Graph.from_dict(data["graph"]) if data.get("graph") else None,
            metadata=data.get("metadata", {}),
            artifacts=[Artifact.from_dict(a) for a in data.get("artifacts", [])],
        )
