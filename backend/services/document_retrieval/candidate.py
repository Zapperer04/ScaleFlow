from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class Candidate:
    id: str
    chunk_id: str
    source: str
    text: str
    score: float
    confidence: float
    retrieval_rank: int = 1
    graph_distance: Optional[int] = None
    entities: List[str] = field(default_factory=list)
    page_numbers: List[int] = field(default_factory=list)
    graph_node_ids: List[str] = field(default_factory=list)
    bbox: Optional[Dict[str, float]] = None
    best_for: List[str] = field(default_factory=list)
    importance: float = 1.0
    section_path: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
