from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class Evidence:
    id: str
    source: str  # e.g., "vector", "graph", "entity", "table", "layout"
    evidence_type: str  # e.g., "chunk", "node", "cell", "block"
    score: float
    confidence: float
    graph_node_ids: List[str] = field(default_factory=list)
    entity_ids: List[str] = field(default_factory=list)
    table_ids: List[str] = field(default_factory=list)
    layout_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
