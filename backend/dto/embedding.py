from pydantic import BaseModel, Field
from typing import List, Dict, Any
from datetime import datetime

class EmbeddingDTO(BaseModel):
    version: str = "v1"
    schema_version: int = 1
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    chunk_id: str
    embedding_vector: List[float]
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": True}
