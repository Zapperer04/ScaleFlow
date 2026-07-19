from abc import ABC, abstractmethod
from execution_engine.core.artifact import ArtifactRef

class ArtifactRegistry(ABC):
    @abstractmethod
    def store(self, content: bytes, content_type: str, version: str) -> ArtifactRef:
        pass
    @abstractmethod
    def load(self, artifact_ref: ArtifactRef) -> bytes:
        pass
