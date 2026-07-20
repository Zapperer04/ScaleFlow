import time
from typing import Dict, Any, Generator, Optional
from execution_engine.data_plane.adapters.base import ResourceProvider
from execution_engine.core.artifact import ArtifactRef
from execution_engine.data_plane.adapters.openrouter_client import OpenRouterClient
from execution_engine.core.provider_session import ProviderSession

class OpenRouterAdapter(ResourceProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.client = OpenRouterClient(api_key=api_key, model=model)

    def get_provider_id(self) -> str:
        return "openrouter"

    def parse(self, artifact: ArtifactRef, prompt_payload: dict, session: Optional[ProviderSession] = None) -> Dict[str, Any]:
        filepath = artifact.uri.replace("file://", "")
        
        # Extract text from the PDF/file to send to OpenRouter
        extracted_text = ""
        if filepath.lower().endswith(".pdf"):
            try:
                import pypdf
                reader = pypdf.PdfReader(filepath)
                extracted_text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
            except Exception:
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        extracted_text = f.read()
                except Exception:
                    pass
        else:
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    extracted_text = f.read()
            except Exception:
                pass

        prompt = (
            f"You are a document understanding engine. Extract the text, layout structure, and semantics from the document.\n"
            f"Here is the document content:\n"
            f"--- START DOCUMENT ---\n"
            f"{extracted_text}\n"
            f"--- END DOCUMENT ---\n\n"
            f"Output a JSON object with the following schema:\n"
            f"{{\n"
            f"  \"nodes\": [\n"
            f"    {{\n"
            f"      \"chunk_id\": \"node1\",\n"
            f"      \"text\": \"<extracted text of the first block, including keys and values>\",\n"
            f"      \"structural_type\": \"heading|paragraph|list_item|table\",\n"
            f"      \"semantic_category\": \"header|body_text|table|footer\"\n"
            f"    }}\n"
            f"  ],\n"
            f"  \"edges\": [\n"
            f"    {{\n"
            f"      \"from\": \"node1\",\n"
            f"      \"to\": \"node2\",\n"
            f"      \"relation\": \"next\"\n"
            f"    }}\n"
            f"  ]\n"
            f"}}\n"
            f"Only output valid JSON, no other text."
        )

        try:
            inference_start = time.time()
            parsed_json, input_tokens, output_tokens = self.client.generate_content(prompt)
            
            if session:
                session.record_duration("inference_time_ms", time.time() - inference_start)
                session.metrics["input_tokens"] = input_tokens
                session.metrics["output_tokens"] = output_tokens
                # OpenRouter cost estimation: input $0.5/M, output $1.5/M (generic baseline)
                session.metrics["cost_estimate"] = (input_tokens * 0.5 / 1000000.0) + (output_tokens * 1.5 / 1000000.0)
                
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
        yield {"chunk": "1"}
        yield {"chunk": "2"}
