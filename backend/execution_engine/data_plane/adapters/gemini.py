import os
import json
import requests
from typing import Dict, Any, Generator
from execution_engine.data_plane.adapters.base import ResourceProvider
from execution_engine.core.artifact import ArtifactRef

class GeminiAdapter(ResourceProvider):
    def get_provider_id(self) -> str:
        return "gemini"

    def parse(self, artifact: ArtifactRef, prompt_payload: dict) -> Dict[str, Any]:
        url = os.environ.get("GEMINI_MOCK_URL", "")
        if url:
            res = requests.post(f"{url}/parse", json={"artifact": artifact.artifact_id, "prompt": prompt_payload, "streaming": False})
            if res.status_code == 429:
                raise Exception("429 Rate Limit Exceeded")
            if res.status_code == 504 or res.status_code == 500:
                raise Exception("Timeout")
            try:
                return res.json()
            except Exception:
                raise Exception("Malformed JSON")
        return {"raw_provider_ast": "gemini_output"}

    def parse_stream(self, artifact: ArtifactRef, prompt_payload: dict) -> Generator[Dict[str, Any], None, None]:
        url = os.environ.get("GEMINI_MOCK_URL", "")
        if url:
            res = requests.post(f"{url}/parse", json={"artifact": artifact.artifact_id, "prompt": prompt_payload, "streaming": True}, stream=True)
            if res.status_code == 429:
                raise Exception("429 Rate Limit Exceeded")
            for line in res.iter_lines():
                if line:
                    try:
                        yield json.loads(line.decode("utf-8"))
                    except Exception:
                        raise Exception("Malformed JSON in stream")
        else:
            yield {"chunk": "1"}
            yield {"chunk": "2"}

