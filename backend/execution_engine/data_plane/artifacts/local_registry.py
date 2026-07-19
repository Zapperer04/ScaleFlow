import os
import hashlib
from execution_engine.data_plane.artifacts.registry import ArtifactRegistry
from execution_engine.core.artifact import ArtifactRef
import uuid

class LocalArtifactRegistry(ArtifactRegistry):
    def __init__(self, base_dir: str = "/tmp/scaleflow/artifacts"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        
    def store(self, content: bytes, content_type: str, version: str) -> ArtifactRef:
        content_hash = hashlib.sha256(content).hexdigest()
        artifact_id = f"art-{uuid.uuid4()}"
        file_path = os.path.join(self.base_dir, f"{artifact_id}.bin")
        with open(file_path, "wb") as f:
            f.write(content)
        return ArtifactRef(
            artifact_id=artifact_id,
            uri=f"file://{file_path}",
            version=version,
            content_type=content_type,
            hash=content_hash
        )
        
    def load(self, artifact_ref: ArtifactRef) -> bytes:
        file_path = artifact_ref.uri.replace("file://", "")
        with open(file_path, "rb") as f:
            return f.read()
