from pydantic import BaseModel, Field
from typing import Dict, Any, List
from execution_engine.core.artifact import ArtifactRef
from execution_engine.core.requirements import ProviderRequirements

class JobSpec(BaseModel):
    id: str
    type: str
    priority: int = 1
    payload: ArtifactRef
    requirements: ProviderRequirements
    
    # Immutable Execution History
    attempts: int = 1
    provider_history: List[str] = Field(default_factory=list)
    failure_history: List[str] = Field(default_factory=list)
    
    # Estimated execution cost metrics
    estimated_cost_tokens: int = 1000
    estimated_latency_seconds: float = 2.0
    
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = {
        "frozen": True
    }
