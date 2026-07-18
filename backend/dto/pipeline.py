from pydantic import BaseModel, Field
from typing import List, Dict, Any
from datetime import datetime

class PipelineStateDTO(BaseModel):
    version: str = "v1"
    schema_version: int = 1
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    pipeline_id: int
    name: str
    state: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": True}
