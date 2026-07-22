from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class BoundingBox:
    ymin: float
    xmin: float
    ymax: float
    xmax: float

    def to_dict(self) -> Dict[str, float]:
        return {"ymin": self.ymin, "xmin": self.xmin, "ymax": self.ymax, "xmax": self.xmax}

@dataclass
class CanonicalBlock:
    id: str
    type: str  # heading, paragraph, table, figure, list, caption, etc.
    text: str
    page: int
    bbox: Optional[BoundingBox] = None
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CanonicalTable:
    id: str
    page: int
    rows: int
    columns: int
    headers: List[str] = field(default_factory=list)
    cells: List[Dict[str, Any]] = field(default_factory=list)
    merged_cells: List[Dict[str, Any]] = field(default_factory=list)
    bbox: Optional[BoundingBox] = None
    caption: Optional[str] = None
    references: List[str] = field(default_factory=list)
    graph_node_id: Optional[str] = None
    chunk_ids: List[str] = field(default_factory=list)

@dataclass
class CanonicalEntity:
    name: str
    type: str  # Person, Organization, Location, Date, Money, Quantity, Identifier, Product, Domain Entity
    normalized_value: str
    aliases: List[str] = field(default_factory=list)
    occurrences: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class CanonicalDocument:
    document_id: str
    document: Dict[str, Any] = field(default_factory=dict)
    pages: List[Dict[str, Any]] = field(default_factory=list)
    blocks: List[CanonicalBlock] = field(default_factory=list)
    sections: List[Dict[str, Any]] = field(default_factory=list)
    graph: Dict[str, Any] = field(default_factory=dict)
    entities: List[CanonicalEntity] = field(default_factory=list)
    tables: List[CanonicalTable] = field(default_factory=list)
    figures: List[Dict[str, Any]] = field(default_factory=list)
    layout: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    parser_metadata: Dict[str, Any] = field(default_factory=dict)

# -----------------
# Derived Schemas
# -----------------

@dataclass
class GraphNode:
    id: str
    type: str
    text: str
    page: int
    bbox: Optional[Dict[str, float]] = None
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunk_ids: List[str] = field(default_factory=list)

@dataclass
class GraphEdge:
    source: str
    target: str
    type: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    builder: str = "GraphBuilder"

@dataclass
class SemanticChunk:
    chunk_id: str
    text: str
    summary: str
    parent_node: str
    section_path: List[str]
    page_range: List[int]
    bbox: Optional[Dict[str, float]] = None
    graph_node_ids: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    table_refs: List[str] = field(default_factory=list)
    figure_refs: List[str] = field(default_factory=list)
    previous_chunk: Optional[str] = None
    next_chunk: Optional[str] = None
    reading_order: int = 0
    importance_score: float = 1.0
    lineage: List[Dict[str, Any]] = field(default_factory=list)
    retrieval_tags: List[str] = field(default_factory=list)
    query_intent: List[str] = field(default_factory=list)
    chunk_type: str = "general"
    priority: float = 1.0
    # Additional Retrieval Hints
    best_for: List[str] = field(default_factory=list)  # semantic, definition, table_lookup, comparison, procedural, entity

@dataclass
class EntityRecord:
    id: str
    name: str
    type: str
    normalized_value: str
    aliases: List[str] = field(default_factory=list)
    occurrences: List[Dict[str, Any]] = field(default_factory=list)
    chunk_ids: List[str] = field(default_factory=list)
    graph_node_ids: List[str] = field(default_factory=list)

@dataclass
class EntityEdge:
    source: str
    target: str
    type: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EntityGraph:
    entities: List[EntityRecord] = field(default_factory=list)
    edges: List[EntityEdge] = field(default_factory=list)

@dataclass
class TableRepresentation:
    id: str
    schema: Dict[str, Any] = field(default_factory=dict)
    headers: List[str] = field(default_factory=list)
    cells: List[Dict[str, Any]] = field(default_factory=list)
    merged_cells: List[Dict[str, Any]] = field(default_factory=list)
    coordinates: Optional[Dict[str, float]] = None
    page: int = 0
    caption: Optional[str] = None
    references: List[str] = field(default_factory=list)
    graph_node_id: Optional[str] = None
    chunk_ids: List[str] = field(default_factory=list)

@dataclass
class LayoutRepresentation:
    reading_order: List[str]
    font_hierarchy: List[Dict[str, Any]] = field(default_factory=list)
    heading_level: Dict[str, int] = field(default_factory=dict)
    visual_blocks: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    columns: List[Dict[str, Any]] = field(default_factory=list)
    page_coordinates: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    style_metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MetadataRepresentation:
    title: str
    author: str
    language: str
    document_type: str
    creation_date: str
    page_count: int
    parser_version: str
    graph_version: str
    document_hash: str

@dataclass
class EmbeddingRecord:
    embedding_id: str
    chunk_id: str
    graph_node_ids: List[str]
    entity_ids: List[str]
    metadata: Dict[str, Any]
    embedding_model: str
    embedding_dimension: int
    embedding_version: str
    created_at: str
    vector_hash: str
    vector: List[float]
