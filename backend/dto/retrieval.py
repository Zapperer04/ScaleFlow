from pydantic import BaseModel, Field
from typing import List, Dict, Any
from datetime import datetime

class RetrievalRequestDTO(BaseModel):
    version: str = "v1"
    schema_version: int = 1
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    query: str
    limit: int = 5
    filters: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": True}

class RetrievalResponseDTO(BaseModel):
    version: str = "v1"
    schema_version: int = 1
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    query: str
    results: List[Dict[str, Any]]
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": True}
