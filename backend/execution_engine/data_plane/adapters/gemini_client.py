import os
import time
import requests
import json
import re
from typing import Dict, Any, Tuple, Optional

class GeminiClient:
    """
    Native, isolated Gemini client. Handles file uploads and content generation.
    Owns HTTP and transport-level retries.
    """
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required but not found in env.")

    def _execute_with_retry(self, method: str, url: str, **kwargs) -> requests.Response:
        max_retries = kwargs.pop("max_retries", 3)
        backoff = 1.0
        last_ex = None
        for attempt in range(max_retries):
            try:
                resp = requests.request(method, url, **kwargs)
                # Retry on transport or transient HTTP status codes (5xx, 408)
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

    def upload_file(self, file_path: str) -> Tuple[str, str]:
        """
        Uploads a file via the Gemini Files API.
        Returns (file_uri, file_name).
        """
        file_size = os.path.getsize(file_path)
        upload_url = f"https://generativelanguage.googleapis.com/upload/v1beta/files?key={self.api_key}"
        headers = {
            "X-Goog-Upload-Protocol": "resumable",
            "X-Goog-Upload-Command": "start",
            "X-Goog-Upload-Header-Content-Length": str(file_size),
            "Content-Type": "application/json",
        }
        metadata = {
            "file": {
                "display_name": os.path.basename(file_path),
                "mime_type": "application/pdf" if file_path.lower().endswith(".pdf") else "image/png",
            }
        }
        
        # 1. Initiate upload session
        res = self._execute_with_retry("POST", upload_url, headers=headers, json=metadata, timeout=30)
        if res.status_code != 200:
            raise Exception(f"Failed to initiate upload: {res.text}")
            
        session_url = res.headers.get("X-Goog-Upload-URL")
        if not session_url:
            raise Exception("No X-Goog-Upload-URL header returned.")
            
        # 2. Upload file bytes
        with open(file_path, "rb") as f:
            data = f.read()
            
        headers = {
            "Content-Length": str(len(data)),
            "X-Goog-Upload-Command": "upload, finalize",
            "X-Goog-Upload-Offset": "0",
        }
        res2 = self._execute_with_retry("POST", session_url, headers=headers, data=data, timeout=120)
        if res2.status_code != 200:
            raise Exception(f"Failed to upload file content: {res2.text}")
            
        res_json = res2.json()
        file_uri = res_json["file"]["uri"]
        file_name = res_json["file"]["name"]
        return file_uri, file_name

    def generate_content(self, prompt: str, file_uri: Optional[str] = None, response_schema: Optional[dict] = None) -> Tuple[Dict[str, Any], int, int]:
        """
        Calls generateContent. Returns (parsed_json_dict, input_tokens, output_tokens).
        """
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        parts = [{"text": prompt}]
        if file_uri:
            parts.append({"fileData": {"mimeType": "application/pdf", "fileUri": file_uri}})
            
        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": 0.0,
                "responseMimeType": "application/json",
            }
        }
        if response_schema:
            payload["generationConfig"]["responseSchema"] = response_schema
            
        res = self._execute_with_retry("POST", url, headers={"Content-Type": "application/json"}, json=payload, timeout=240)
        if res.status_code != 200:
            raise Exception(f"Gemini API failure: status_code={res.status_code}, response={res.text}")
            
        res_json = res.json()
        candidates = res_json.get("candidates", [])
        if not candidates:
            raise Exception("No candidates in Gemini response")
            
        finish_reason = candidates[0].get("finishReason")
        if finish_reason not in ("STOP", None):
            raise Exception(f"Gemini processing stopped early due to finishReason={finish_reason}")
            
        text_parts = candidates[0].get("content", {}).get("parts", [])
        if not text_parts:
            raise Exception("No text parts returned by Gemini")
            
        text = text_parts[0].get("text", "")
        # Clean potential markdown wrappers
        cleaned = re.sub(r"^```json\s*", "", text)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            parsed = json.loads(cleaned.strip())
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse Gemini JSON output: {e}. Raw response: {text}")
            
        metadata = res_json.get("usageMetadata", {})
        input_tokens = metadata.get("promptTokenCount", 0)
        output_tokens = metadata.get("candidatesTokenCount", 0)
        
        return parsed, input_tokens, output_tokens
