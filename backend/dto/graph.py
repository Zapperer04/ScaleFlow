from pydantic import BaseModel, Field
from typing import List, Dict, Any
from datetime import datetime

class MetadataDTO(BaseModel):
    version: str = "v1"
    schema_version: int = 1
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    fields: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": True}

class NodeDTO(BaseModel):
    version: str = "v1"
    schema_version: int = 1
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    node_id: str
    label: str
    properties: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": True}

class EdgeDTO(BaseModel):
    version: str = "v1"
    schema_version: int = 1
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    source: str
    target: str
    relation: str
    properties: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": True}

class GraphDTO(BaseModel):
    version: str = "v1"
    schema_version: int = 1
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    nodes: List[NodeDTO]
    edges: List[EdgeDTO]

    model_config = {"frozen": True}
