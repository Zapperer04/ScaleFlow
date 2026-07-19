from dataclasses import dataclass
from typing import Dict, Any
from backend.domain.value_objects.node_id import NodeId

@dataclass(frozen=True)
class Node:
    node_id: NodeId
    label: str
    properties: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id.to_dict(),
            "label": self.label,
            "properties": self.properties,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Node":
        return cls(
            node_id=NodeId.from_dict(data["node_id"]),
            label=str(data["label"]),
            properties=data.get("properties", {}),
        )
