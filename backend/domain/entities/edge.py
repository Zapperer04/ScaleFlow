from dataclasses import dataclass
from typing import Dict, Any
from backend.domain.value_objects.node_id import NodeId

@dataclass(frozen=True)
class Edge:
    source: NodeId
    target: NodeId
    relation: str
    properties: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source.to_dict(),
            "target": self.target.to_dict(),
            "relation": self.relation,
            "properties": self.properties,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Edge":
        return cls(
            source=NodeId.from_dict(data["source"]),
            target=NodeId.from_dict(data["target"]),
            relation=str(data["relation"]),
            properties=data.get("properties", {}),
        )
