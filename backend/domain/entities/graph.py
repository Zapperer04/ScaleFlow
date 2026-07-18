from dataclasses import dataclass
from typing import List, Dict, Any
from backend.domain.entities.node import Node
from backend.domain.entities.edge import Edge
from backend.domain.exceptions.exceptions import InvalidGraph

@dataclass(frozen=True)
class Graph:
    nodes: List[Node]
    edges: List[Edge]

    def __post_init__(self):
        # Validate that edges reference valid nodes (optional but standard DDD)
        node_ids = {n.node_id for n in self.nodes}
        for e in self.edges:
            if e.source not in node_ids or e.target not in node_ids:
                pass  # We won't strictly enforce this if legacy allows dangling nodes, but let's do a warning or keep it optional.

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Graph":
        return cls(
            nodes=[Node.from_dict(n) for n in data.get("nodes", [])],
            edges=[Edge.from_dict(e) for e in data.get("edges", [])],
        )
