import time
from typing import Dict, Any, Generator, Optional
from execution_engine.data_plane.adapters.base import ResourceProvider
from execution_engine.core.artifact import ArtifactRef
from execution_engine.data_plane.adapters.gemini_client import GeminiClient
from execution_engine.core.provider_session import ProviderSession

class GeminiAdapter(ResourceProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.client = GeminiClient(api_key=api_key, model=model)

    def get_provider_id(self) -> str:
        return "gemini"

    def parse(self, artifact: ArtifactRef, prompt_payload: dict, session: Optional[ProviderSession] = None) -> Dict[str, Any]:
        filepath = artifact.uri.replace("file://", "")
        
        prompt = (
            "You are a document understanding engine. Extract the text, layout structure, and semantics from the document.\n"
            "Output a JSON object with the following schema:\n"
            "{\n"
            "  \"nodes\": [\n"
            "    {\n"
            "      \"chunk_id\": \"node1\",\n"
            "      \"text\": \"<extracted text of the first block, including keys and values>\",\n"
            "      \"structural_type\": \"heading|paragraph|list_item|table\",\n"
            "      \"semantic_category\": \"header|body_text|table|footer\"\n"
            "    }\n"
            "  ],\n"
            "  \"edges\": [\n"
            "    {\n"
            "      \"from\": \"node1\",\n"
            "      \"to\": \"node2\",\n"
            "      \"relation\": \"next\"\n"
            "    }\n"
            "  ]\n"
            "}\n"
            "Only output valid JSON, no other text."
        )

        try:
            # 1. Upload file (measure wait)
            upload_start = time.time()
            file_uri, _ = self.client.upload_file(filepath)
            if session:
                session.record_duration("provider_wait_ms", time.time() - upload_start)

            # 2. Generate Content (measure inference)
            inference_start = time.time()
            parsed_json, input_tokens, output_tokens = self.client.generate_content(prompt, file_uri=file_uri)
            
            if session:
                session.record_duration("inference_time_ms", time.time() - inference_start)
                session.metrics["input_tokens"] = input_tokens
                session.metrics["output_tokens"] = output_tokens
                # Cost estimate: input $2.5/M, output $10/M tokens
                session.metrics["cost_estimate"] = (input_tokens * 2.5 / 1000000.0) + (output_tokens * 10.0 / 1000000.0)
                
            return parsed_json
            
        except Exception as e:
            err_msg = str(e).lower()
            layer = "Provider"
            if "connection" in err_msg or "timeout" in err_msg:
                layer = "Transport"
            elif "429" in err_msg:
                layer = "Provider"
            elif "json" in err_msg or "decode" in err_msg:
                layer = "Schema"
                
            if session:
                session.mark_failure(layer, str(e))
            raise e

    def parse_stream(self, artifact: ArtifactRef, prompt_payload: dict) -> Generator[Dict[str, Any], None, None]:
        # Fallback stream yielding chunks
        yield {"chunk": "1"}
        yield {"chunk": "2"}
