from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime

class WorkerTaskDTO(BaseModel):
    version: str = "v1"
    schema_version: int = 1
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    task_id: int
    task_type: str
    task_data: Dict[str, Any]
    priority: str
    assigned_worker_id: Optional[str] = None

    model_config = {"frozen": True}
