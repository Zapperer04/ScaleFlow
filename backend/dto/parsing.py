from pydantic import BaseModel, Field
from typing import Dict, Any, List
from datetime import datetime

class ParserResponseDTO(BaseModel):
    version: str = "v1"
    schema_version: int = 1
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    
    document_type: str
    pages: List[Dict[str, Any]]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timings: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": True}
