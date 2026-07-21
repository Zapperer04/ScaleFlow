import os
import time
import requests
import json
import re
from typing import Dict, Any, Tuple, Optional


class RateLimitError(Exception):
    """Raised on HTTP 429. Carries retry_after and failure layer metadata."""
    def __init__(self, message: str, retry_after: float = 0.0, provider: str = "gemini"):
        super().__init__(message)
        self.retry_after = retry_after
        self.provider = provider
        self.failure_layer = "Provider"
        self.root_cause = "HTTP_429_QUOTA_EXHAUSTED"
        self.retry_decision = "WAIT_COOLDOWN"
        self.cooldown_applied = retry_after > 0.0


class TransportError(Exception):
    """Network / timeout errors."""
    def __init__(self, message: str):
        super().__init__(message)
        self.failure_layer = "Transport"
        self.root_cause = "NETWORK_FAILURE"
        self.retry_decision = "RETRY_WITH_BACKOFF"
        self.cooldown_applied = False


class SchemaError(Exception):
    """Malformed JSON / schema mismatch."""
    def __init__(self, message: str):
        super().__init__(message)
        self.failure_layer = "Schema"
        self.root_cause = "JSON_PARSE_FAILURE"
        self.retry_decision = "RETRY_OTHER_PROVIDER"
        self.cooldown_applied = False


class GeminiClient:
    """
    Native, isolated Gemini client.
    - Parses Retry-After header on 429 responses.
    - Raises typed exceptions: RateLimitError, TransportError, SchemaError.
    - Does NOT retry on 429 — caller (worker / benchmark) handles pacing.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required but not found in env.")

    def _parse_retry_after(self, response: requests.Response) -> float:
        """Extract Retry-After seconds from response headers."""
        ra = response.headers.get("Retry-After") or response.headers.get("retry-after")
        if ra:
            try:
                return float(ra)
            except ValueError:
                pass
        # Try parsing from response body
        try:
            body = response.json()
            details = body.get("error", {}).get("details", [])
            for d in details:
                if d.get("@type", "").endswith("RetryInfo"):
                    delay = d.get("retryDelay", "")
                    if delay.endswith("s"):
                        return float(delay[:-1])
        except Exception:
            pass
        return 0.0

    def _execute_transport(self, method: str, url: str, **kwargs) -> requests.Response:
        """Execute a single HTTP call. Raises TransportError on network issues."""
        try:
            resp = requests.request(method, url, **kwargs)
            return resp
        except (requests.ConnectionError, requests.Timeout, ConnectionError) as e:
            raise TransportError(f"Network failure: {e}")

    def _execute_with_retry(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Retry on transient 5xx / transport errors.
        Do NOT retry on 429 — surface it immediately so the caller can pace.
        """
        max_retries = kwargs.pop("max_retries", 3)
        backoff = 1.0
        last_ex = None

        for attempt in range(max_retries):
            try:
                resp = self._execute_transport(method, url, **kwargs)

                # Surface 429 immediately — do not retry
                if resp.status_code == 429:
                    retry_after = self._parse_retry_after(resp)
                    raise RateLimitError(
                        f"Gemini 429: quota exhausted. Retry-After={retry_after:.0f}s",
                        retry_after=retry_after,
                        provider="gemini",
                    )

                # Retry transient errors
                if resp.status_code in (408, 500, 502, 503, 504):
                    raise TransportError(f"HTTP {resp.status_code} transient error")

                return resp

            except RateLimitError:
                raise  # Never retry 429 here
            except TransportError as e:
                last_ex = e
                if attempt == max_retries - 1:
                    raise
                time.sleep(backoff)
                backoff = min(backoff * 2, 30.0)

        raise last_ex or TransportError("Request failed after retries")

    def upload_file(self, file_path: str) -> Tuple[str, str]:
        """
        Uploads a file via the Gemini Files API.
        Returns (file_uri, file_name).
        Raises RateLimitError if 429 received during upload.
        """
        file_size = os.path.getsize(file_path)
        upload_url = (
            f"https://generativelanguage.googleapis.com/upload/v1beta/files"
            f"?key={self.api_key}"
        )
        headers = {
            "X-Goog-Upload-Protocol": "resumable",
            "X-Goog-Upload-Command": "start",
            "X-Goog-Upload-Header-Content-Length": str(file_size),
            "Content-Type": "application/json",
        }
        metadata = {
            "file": {
                "display_name": os.path.basename(file_path),
                "mime_type": (
                    "application/pdf" if file_path.lower().endswith(".pdf") else "image/png"
                ),
            }
        }

        res = self._execute_with_retry("POST", upload_url, headers=headers, json=metadata, timeout=30)
        if res.status_code != 200:
            raise TransportError(f"Failed to initiate upload: {res.text}")

        session_url = res.headers.get("X-Goog-Upload-URL")
        if not session_url:
            raise TransportError("No X-Goog-Upload-URL header returned.")

        with open(file_path, "rb") as f:
            data = f.read()

        headers2 = {
            "Content-Length": str(len(data)),
            "X-Goog-Upload-Command": "upload, finalize",
            "X-Goog-Upload-Offset": "0",
        }
        res2 = self._execute_with_retry("POST", session_url, headers=headers2, data=data, timeout=120)
        if res2.status_code != 200:
            raise TransportError(f"Failed to upload file content: {res2.text}")

        res_json = res2.json()
        file_uri = res_json["file"]["uri"]
        file_name = res_json["file"]["name"]
        return file_uri, file_name

    def generate_content(
        self,
        prompt: str,
        file_uri: Optional[str] = None,
        response_schema: Optional[dict] = None,
    ) -> Tuple[Dict[str, Any], int, int]:
        """
        Calls generateContent.
        Returns (parsed_json_dict, input_tokens, output_tokens).
        Raises:
          - RateLimitError on 429
          - TransportError on network/5xx
          - SchemaError on JSON parse failure
        """
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        parts = [{"text": prompt}]
        if file_uri:
            parts.append({"fileData": {"mimeType": "application/pdf", "fileUri": file_uri}})

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": 0.0,
                "responseMimeType": "application/json",
            },
        }
        if response_schema:
            payload["generationConfig"]["responseSchema"] = response_schema

        res = self._execute_with_retry(
            "POST", url,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=240,
        )

        if res.status_code != 200:
            raise TransportError(
                f"Gemini API failure: status_code={res.status_code}, response={res.text}"
            )

        res_json = res.json()
        candidates = res_json.get("candidates", [])
        if not candidates:
            raise SchemaError("No candidates in Gemini response")

        finish_reason = candidates[0].get("finishReason")
        if finish_reason not in ("STOP", None):
            raise SchemaError(f"Gemini stopped early: finishReason={finish_reason}")

        text_parts = candidates[0].get("content", {}).get("parts", [])
        if not text_parts:
            raise SchemaError("No text parts returned by Gemini")

        text = text_parts[0].get("text", "")
        cleaned = re.sub(r"^```json\s*", "", text)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            parsed = json.loads(cleaned.strip())
        except json.JSONDecodeError as e:
            raise SchemaError(
                f"Failed to parse Gemini JSON output: {e}. Raw response: {text[:200]}"
            )

        metadata = res_json.get("usageMetadata", {})
        input_tokens = metadata.get("promptTokenCount", 0)
        output_tokens = metadata.get("candidatesTokenCount", 0)

        return parsed, input_tokens, output_tokens
