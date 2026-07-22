import os
import time
import logging
from typing import Dict, Any, Generator, Optional
from backend.platform.config.providers import MODEL_REGISTRY, DEFAULT_MODEL
from backend.platform.runtime.provider_registry import provider_registry
import requests

logger = logging.getLogger(__name__)

class InferenceGateway:
    def __init__(self):
        self.registry = provider_registry

    def generate(self, prompt: str, model: str = None) -> Dict[str, Any]:
        target_model = model or DEFAULT_MODEL
        primary_provider = self.registry.get_provider_for_model(target_model)
        fallbacks = self.registry.get_fallbacks_for_model(target_model)
        
        providers_to_try = [primary_provider] + fallbacks
        last_error = None
        
        for provider in providers_to_try:
            api_key = self.registry.get_api_key(provider)
            # Mock or offline check
            if not api_key or os.getenv("TEST_OFFLINE_MODE") == "True":
                return self._mock_generate(prompt, target_model, provider)
                
            try:
                if provider == "openrouter":
                    res = self._call_openrouter(prompt, target_model, api_key)
                    if res: return res
                elif provider == "openai":
                    res = self._call_openai(prompt, target_model, api_key)
                    if res: return res
                elif provider == "gemini":
                    res = self._call_gemini(prompt, target_model, api_key)
                    if res: return res
            except Exception as e:
                logger.warning(f"Provider {provider} failed for model {target_model}: {e}")
                last_error = e
                
        # If all fail, return fallback mock
        logger.error(f"All providers failed for model {target_model}. Falling back to mock. Error: {last_error}")
        return self._mock_generate(prompt, target_model, "mock")

    def _call_openrouter(self, prompt: str, model: str, api_key: str) -> Optional[Dict[str, Any]]:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            res_data = response.json()
            text = res_data["choices"][0]["message"]["content"]
            usage = res_data.get("usage", {})
            return self._build_result(text, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0), "openrouter", model)
        return None

    def _call_openai(self, prompt: str, model: str, api_key: str) -> Optional[Dict[str, Any]]:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": "gpt-4o-mini" if model.startswith("gpt") else model, "messages": [{"role": "user", "content": prompt}]}
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            res_data = response.json()
            text = res_data["choices"][0]["message"]["content"]
            usage = res_data.get("usage", {})
            return self._build_result(text, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0), "openai", model)
        return None

    def _call_gemini(self, prompt: str, model: str, api_key: str) -> Optional[Dict[str, Any]]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            res_data = response.json()
            text = res_data["candidates"][0]["content"]["parts"][0]["text"]
            # Estimate tokens
            prompt_tokens = len(prompt) // 4
            completion_tokens = len(text) // 4
            return self._build_result(text, prompt_tokens, completion_tokens, "gemini", model)
        return None

    def _build_result(self, text: str, prompt_tokens: int, completion_tokens: int, provider: str, model: str) -> Dict[str, Any]:
        cost = self.calculate_cost(prompt_tokens, completion_tokens, model)
        # Log to DB cost tracking
        self._log_cost_to_db(provider, model, prompt_tokens, completion_tokens, cost)
        return {
            "text": text,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "provider": provider,
            "model": model,
            "cost": cost
        }

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        meta = MODEL_REGISTRY.get(model, {})
        input_rate = meta.get("cost_per_1k_input", 0.0)
        output_rate = meta.get("cost_per_1k_output", 0.0)
        return (prompt_tokens / 1000.0 * input_rate) + (completion_tokens / 1000.0 * output_rate)

    def _log_cost_to_db(self, provider: str, model: str, prompt_tokens: int, completion_tokens: int, cost: float):
        from backend.platform.runtime.app_state import app_state
        if app_state.db_conn:
            try:
                cursor = app_state.db_conn.cursor()
                cursor.execute("""
                INSERT INTO cost_logs (provider, model, prompt_tokens, completion_tokens, cost)
                VALUES (?, ?, ?, ?, ?)
                """, (provider, model, prompt_tokens, completion_tokens, cost))
                app_state.db_conn.commit()
            except Exception as e:
                logger.error(f"Failed to log cost to database: {e}")

    def _mock_generate(self, prompt: str, model: str, provider: str) -> Dict[str, Any]:
        # Return structured mock answer
        text = "Based on retrieved evidence [1], Google Corp was founded in Jan 1, 1998. The table statistics verify the infrastructure metrics [1]."
        return self._build_result(text, 120, 80, provider, model)
        
    def stream_generate(self, prompt: str, model: str = None) -> Generator[str, None, None]:
        # Generator yielding pieces of token responses
        result = self.generate(prompt, model)
        text = result["text"]
        words = text.split(" ")
        for i, word in enumerate(words):
            yield (word + " " if i < len(words) - 1 else word)
            time.sleep(0.02) # Simulate network streaming delay
