from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class ChunkDTO(BaseModel):
    version: str = "v1"
    schema_version: int = 1
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    chunk_id: str
    chunk_index: int
    chunk_text: str
    page_number: int
    file_id: int
    pipeline_id: int
    metadata: Dict[str, Any] = Field(default_factory=dict)
    graph_relations: Optional[Any] = None

    model_config = {"frozen": True}
