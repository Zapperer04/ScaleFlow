import os
import time
import requests
import json
import re
from typing import Dict, Any, Tuple, Optional

class OpenRouterClient:
    """
    Native, isolated OpenRouter client. Handles completions using configured model.
    Owns HTTP and transport-level retries.
    """
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model = model or os.getenv("OPENROUTER_MODEL", "google/gemma-2-9b-it:free")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is required but not found in env.")

    def _execute_with_retry(self, method: str, url: str, **kwargs) -> requests.Response:
        max_retries = kwargs.pop("max_retries", 3)
        backoff = 1.0
        last_ex = None
        for attempt in range(max_retries):
            try:
                resp = requests.request(method, url, **kwargs)
                if resp.status_code in (408, 500, 502, 503, 504):
                    raise requests.RequestException(f"HTTP Status {resp.status_code}")
                return resp
            except (requests.RequestException, ConnectionError, TimeoutError) as e:
                last_ex = e
                if attempt == max_retries - 1:
                    raise e
                time.sleep(backoff)
                backoff *= 2
        raise last_ex or Exception("Request failed after retries")

    def generate_content(self, prompt: str, base64_image: Optional[str] = None, response_schema: Optional[dict] = None) -> Tuple[Dict[str, Any], int, int]:
        """
        Calls chat/completions endpoint on OpenRouter.
        Returns (parsed_json_dict, input_tokens, output_tokens).
        """
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        content_parts = [{"type": "text", "text": prompt}]
        if base64_image:
            content_parts.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64_image}"
                }
            })
            
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": content_parts}],
            "temperature": 0.0,
            "max_tokens": 4000
        }
        
        # OpenRouter JSON mode format if requested
        if response_schema:
            payload["response_format"] = {"type": "json_object"}
            
        res = self._execute_with_retry("POST", url, headers=headers, json=payload, timeout=240)
        if res.status_code != 200:
            raise Exception(f"OpenRouter API failure: status_code={res.status_code}, response={res.text}")
            
        data = res.json()
        choices = data.get("choices", [])
        if not choices:
            raise Exception("No choices in OpenRouter response")
            
        text = choices[0]["message"]["content"]
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
            
        try:
            parsed = json.loads(cleaned.strip())
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse OpenRouter JSON output: {e}. Raw response: {text}")
            
        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        
        return parsed, input_tokens, output_tokens
