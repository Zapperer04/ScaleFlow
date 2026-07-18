from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime

class StorageArtifactDTO(BaseModel):
    version: str = "v1"
    schema_version: int = 1
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    artifact_id: Optional[int] = None
    pipeline_id: int
    task_id: Optional[int] = None
    artifact_type: str
    storage_uri: str
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    checksum: Optional[str] = None

    model_config = {"frozen": True}
