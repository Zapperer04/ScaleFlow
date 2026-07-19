from typing import Dict, Any, Generator
from execution_engine.data_plane.adapters.base import ResourceProvider
from execution_engine.core.artifact import ArtifactRef

class GeminiAdapter(ResourceProvider):
    def get_provider_id(self) -> str:
        return "gemini"
    def parse(self, artifact: ArtifactRef, prompt_payload: dict) -> Dict[str, Any]:
        return {"raw_provider_ast": "gemini_output"}
    def parse_stream(self, artifact: ArtifactRef, prompt_payload: dict) -> Generator[Dict[str, Any], None, None]:
        yield {"chunk": "1"}
        yield {"chunk": "2"}
