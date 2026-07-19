from abc import ABC, abstractmethod
from typing import Dict, Any, Generator
from execution_engine.core.artifact import ArtifactRef

class ResourceProvider(ABC):
    @abstractmethod
    def get_provider_id(self) -> str:
        pass
    @abstractmethod
    def parse(self, artifact: ArtifactRef, prompt_payload: dict) -> Dict[str, Any]:
        pass
    @abstractmethod
    def parse_stream(self, artifact: ArtifactRef, prompt_payload: dict) -> Generator[Dict[str, Any], None, None]:
        pass
