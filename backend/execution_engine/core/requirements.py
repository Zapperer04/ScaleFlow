from pydantic import BaseModel
from typing import Optional

class ProviderRequirements(BaseModel):
    """
    Capability requirements for a provider to execute a JobSpec.
    This defines what the VLM Execution Engine expects from the provider.
    """
    multimodal: bool = False
    streaming: bool = False
    schema_version: Optional[str] = None
    context_window: int = 4096
    priority: int = 1  # 0 is highest
    max_cost_per_1k_tokens: Optional[float] = None
