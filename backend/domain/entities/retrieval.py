from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass(frozen=True)
class Retrieval:
    query: str
    results: List[Dict[str, Any]]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "results": self.results,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Retrieval":
        return cls(
            query=str(data["query"]),
            results=list(data.get("results", [])),
            metadata=data.get("metadata", {}),
        )
