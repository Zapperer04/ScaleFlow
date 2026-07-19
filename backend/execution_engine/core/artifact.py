from pydantic import BaseModel, Field
from typing import Optional

class ArtifactRef(BaseModel):
    """
    Reference to a versioned artifact stored in the Artifact Registry.
    Keeps workers stateless by ensuring they only deal with artifact URIs, not binary data in memory where possible.
    """
    artifact_id: str
    uri: str
    version: str
    content_type: str
    hash: Optional[str] = None
    
    model_config = {
        "frozen": True  # Immutable
    }
