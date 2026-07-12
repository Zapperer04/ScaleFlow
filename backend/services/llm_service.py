"""
answer_generation.py — Multi‑provider LLM answer synthesis with retries,
token management, telemetry, and heuristic fallback.
"""

import os
import re
import time
import logging
import threading
from typing import List, Dict, Any, Optional, Tuple, Type, Set
from abc import ABC, abstractmethod

import requests

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------
LLM_TIMEOUT = getattr(config, "LLM_TIMEOUT", 15)
LLM_TEMPERATURE = getattr(config, "LLM_TEMPERATURE", 0.2)
LLM_OUTPUT_MAX_TOKENS = getattr(config, "LLM_OUTPUT_MAX_TOKENS", 512)
LLM_CONTEXT_WINDOW = getattr(config, "LLM_CONTEXT_WINDOW", 128000)
LLM_RETRY_MAX = getattr(config, "LLM_RETRY_MAX", 2)
LLM_RETRY_DELAY_BASE = getattr(config, "LLM_RETRY_DELAY_BASE", 1.0)
LLM_RESERVED_PROMPT_TOKENS = getattr(config, "LLM_RESERVED_PROMPT_TOKENS", 1024)

# Provider order
LLM_PROVIDER_ORDER = getattr(config, "LLM_PROVIDER_ORDER", ["groq", "openai", "ollama"])

# Model names per provider
LLM_MODELS = getattr(config, "LLM_MODELS", {
    "groq": "llama-3.1-8b-instant",
    "openai": "gpt-4o-mini",
    "ollama": "llama3",
})

# Retry‑eligible status codes and exceptions
RETRYABLE_STATUS_CODES: Set[int] = {429, 500, 502, 503, 504}
RETRYABLE_EXCEPTIONS = (requests.Timeout, requests.ConnectionError)

# ------------------------------------------------------------------------------
# Token estimation
# ------------------------------------------------------------------------------
try:
    import tiktoken
    _enc = tiktoken.encoding_for_model("gpt-4o-mini")
except Exception:
    _enc = None

def _estimate_tokens(text: str) -> int:
    if _enc:
        return len(_enc.encode(text))
    return len(text) // 4

def _truncate_context_to_budget(context: str, max_tokens: int) -> str:
    """Truncate context to fit within max_tokens, preserving sentence boundaries."""
    if not context:
        return context
    tokens = _estimate_tokens(context)
    if tokens <= max_tokens:
        return context
    # Try to cut at sentence boundary
    ratio = max_tokens / tokens
    new_len = int(len(context) * ratio * 1.1)  # slightly over, then trim
    # Find last sentence boundary
    cut = context[:new_len].rfind('.') + 1
    if cut < new_len * 0.5:
        cut = context[:new_len].rfind(' ') + 1
    if cut < new_len * 0.3:
        cut = new_len
    return context[:cut] + "..."

# ------------------------------------------------------------------------------
# Retry helper
# ------------------------------------------------------------------------------
def _retry_request(func, *args, **kwargs):
    """Retry a request with exponential backoff, only on retryable errors."""
    timeout = kwargs.pop("timeout", LLM_TIMEOUT)
    for attempt in range(LLM_RETRY_MAX + 1):
        try:
            resp = func(*args, timeout=timeout, **kwargs)
            if resp.status_code in RETRYABLE_STATUS_CODES:
                if attempt == LLM_RETRY_MAX:
                    raise RuntimeError(f"HTTP {resp.status_code} after {LLM_RETRY_MAX+1} attempts")
                delay = LLM_RETRY_DELAY_BASE * (2 ** attempt)
                logger.warning(f"Retryable HTTP {resp.status_code} (attempt {attempt+1}). Retrying in {delay:.2f}s")
                time.sleep(delay)
                continue
            return resp
        except RETRYABLE_EXCEPTIONS as e:
            if attempt == LLM_RETRY_MAX:
                raise RuntimeError(f"Request failed after {LLM_RETRY_MAX+1} attempts: {e}")
            delay = LLM_RETRY_DELAY_BASE * (2 ** attempt)
            logger.warning(f"Retryable error (attempt {attempt+1}): {e}. Retrying in {delay:.2f}s")
            time.sleep(delay)
            continue
        except Exception as e:
            # Non‑retryable exception
            raise RuntimeError(f"Non‑retryable error: {e}")
    return None

# ------------------------------------------------------------------------------
# Base LLM Provider
# ------------------------------------------------------------------------------
class LLMProvider(ABC):
    name: str = "base"
    model: str = ""

    def __init__(self):
        self._session = requests.Session()

    @abstractmethod
    def _build_payload(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def _parse_response(self, response: Dict[str, Any]) -> Tuple[str, int, int]:
        """
        Parse the raw response.
        Returns (answer_text, prompt_tokens, completion_tokens)
        Raises ValueError if finish_reason is not "stop".
        """
        pass

    def generate(self, system_prompt: str, user_prompt: str) -> Tuple[str, int, int]:
        """Execute a generation with retries."""
        payload = self._build_payload(system_prompt, user_prompt)
        headers = self._headers()
        start = time.perf_counter()
        resp = _retry_request(
            self._session.post,
            self._endpoint(),
            json=payload,
            headers=headers,
            timeout=LLM_TIMEOUT,
        )
        if resp is None:
            raise RuntimeError(f"{self.name} request failed after retries")
        if resp.status_code != 200:
            raise RuntimeError(f"{self.name} HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        answer, ptokens, ctokens = self._parse_response(data)
        latency = time.perf_counter() - start
        logger.debug(f"{self.name} generation: {len(answer)} chars, {ptokens} prompt tokens, {ctokens} completion tokens, {latency*1000:.1f}ms")
        return answer, ptokens, ctokens

    def _headers(self) -> Dict[str, str]:
        return {"Content-Type": "application/json"}

    def _endpoint(self) -> str:
        raise NotImplementedError

# ------------------------------------------------------------------------------
# Groq Provider
# ------------------------------------------------------------------------------
class GroqProvider(LLMProvider):
    name = "groq"

    def __init__(self):
        super().__init__()
        self._api_key = os.environ.get("GROQ_API_KEY")
        if not self._api_key:
            raise ValueError("GROQ_API_KEY not set")
        self.model = LLM_MODELS.get("groq", "llama-3.1-8b-instant")

    def _endpoint(self) -> str:
        return "https://api.groq.com/openai/v1/chat/completions"

    def _headers(self) -> Dict[str, str]:
        h = super()._headers()
        h["Authorization"] = f"Bearer {self._api_key}"
        return h

    def _build_payload(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": LLM_TEMPERATURE,
            "max_tokens": LLM_OUTPUT_MAX_TOKENS,
        }

    def _parse_response(self, data: Dict[str, Any]) -> Tuple[str, int, int]:
        if "choices" not in data or not data["choices"]:
            raise ValueError("No choices in response")
        choice = data["choices"][0]
        finish = choice.get("finish_reason")
        if finish != "stop":
            raise ValueError(f"finish_reason='{finish}' (expected 'stop')")
        message = choice.get("message", {})
        content = message.get("content", "").strip()
        usage = data.get("usage", {})
        ptokens = usage.get("prompt_tokens", 0)
        ctokens = usage.get("completion_tokens", 0)
        return content, ptokens, ctokens

# ------------------------------------------------------------------------------
# OpenAI Provider
# ------------------------------------------------------------------------------
class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self):
        super().__init__()
        self._api_key = os.environ.get("OPENAI_API_KEY")
        if not self._api_key:
            raise ValueError("OPENAI_API_KEY not set")
        self.model = LLM_MODELS.get("openai", "gpt-4o-mini")

    def _endpoint(self) -> str:
        return "https://api.openai.com/v1/chat/completions"

    def _headers(self) -> Dict[str, str]:
        h = super()._headers()
        h["Authorization"] = f"Bearer {self._api_key}"
        return h

    def _build_payload(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": LLM_TEMPERATURE,
            "max_tokens": LLM_OUTPUT_MAX_TOKENS,
        }

    def _parse_response(self, data: Dict[str, Any]) -> Tuple[str, int, int]:
        if "choices" not in data or not data["choices"]:
            raise ValueError("No choices in response")
        choice = data["choices"][0]
        finish = choice.get("finish_reason")
        if finish != "stop":
            raise ValueError(f"finish_reason='{finish}' (expected 'stop')")
        message = choice.get("message", {})
        content = message.get("content", "").strip()
        usage = data.get("usage", {})
        ptokens = usage.get("prompt_tokens", 0)
        ctokens = usage.get("completion_tokens", 0)
        return content, ptokens, ctokens

# ------------------------------------------------------------------------------
# Ollama Provider
# ------------------------------------------------------------------------------
class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self):
        super().__init__()
        self.host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self.model = LLM_MODELS.get("ollama", "llama3")

    def _endpoint(self) -> str:
        return f"{self.host}/api/generate"

    def _build_payload(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        return {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": LLM_TEMPERATURE,
                "num_predict": LLM_OUTPUT_MAX_TOKENS,
            }
        }

    def _parse_response(self, data: Dict[str, Any]) -> Tuple[str, int, int]:
        content = data.get("response", "").strip()
        if not content:
            raise ValueError("Empty response from Ollama")
        return content, 0, 0

# ------------------------------------------------------------------------------
# Provider Registry (thread‑safe cache)
# ------------------------------------------------------------------------------
_PROVIDER_REGISTRY: Dict[str, Type[LLMProvider]] = {
    "groq": GroqProvider,
    "openai": OpenAIProvider,
    "ollama": OllamaProvider,
}
_PROVIDER_CACHE: Dict[str, Optional[LLMProvider]] = {}
_PROVIDER_LOCK = threading.Lock()

def get_provider(name: str) -> Optional[LLMProvider]:
    """Return a cached provider instance, creating it if necessary (thread‑safe)."""
    key = name.lower()
    with _PROVIDER_LOCK:
        if key in _PROVIDER_CACHE:
            return _PROVIDER_CACHE[key]
        cls = _PROVIDER_REGISTRY.get(key)
        if not cls:
            _PROVIDER_CACHE[key] = None
            return None
        try:
            instance = cls()
            _PROVIDER_CACHE[key] = instance
            return instance
        except Exception as e:
            logger.warning(f"Failed to initialize {name} provider: {e}")
            _PROVIDER_CACHE[key] = None
            return None

# ------------------------------------------------------------------------------
# Query type detection (used by SemanticContextBuilder)
# ------------------------------------------------------------------------------
def _detect_query_type(query: str) -> str:
    """Lightweight fallback; ideally reuse IntentService when available."""
    query_lower = query.lower()
    if any(p in query_lower for p in ["who is", "who are", "inventor", "author", "applicant", "person", "contributor"]):
        return "ENTITY_LOOKUP"
    elif any(p in query_lower for p in ["what is the", "number", "date", "id", "filing", "publication", "version", "application"]):
        return "ATTRIBUTE_LOOKUP"
    elif any(p in query_lower for p in ["relation", "connect", "link", "between", "associated"]):
        return "RELATIONSHIP_QUERY"
    elif any(p in query_lower for p in ["summarize", "summary", "overview", "abstract"]):
        return "SUMMARY_QUERY"
    elif any(p in query_lower for p in ["why", "how does", "reason", "explain", "improve"]):
        return "REASONING_QUERY"
    elif any(p in query_lower for p in ["list all", "all dates", "all organisations", "aggregate", "dates"]):
        return "AGGREGATION_QUERY"
    return "ENTITY_LOOKUP"

# ------------------------------------------------------------------------------
# Semantic context builder with token budgeting
# ------------------------------------------------------------------------------
def _build_context(chunks: List[Dict[str, Any]], query: str) -> str:
    """
    Build context using SemanticContextBuilder if available,
    then apply token budgeting.
    """
    # Calculate budget for context
    available_tokens = LLM_CONTEXT_WINDOW - LLM_RESERVED_PROMPT_TOKENS - LLM_OUTPUT_MAX_TOKENS
    if available_tokens < 100:
        available_tokens = 4096  # fallback

    # Try to use SemanticContextBuilder
    try:
        from services.semantic_context_builder import SemanticContextBuilder
        builder = SemanticContextBuilder()
        query_type = _detect_query_type(query)
        context = builder.build(query_type, chunks)
        if context and context.strip():
            # Truncate if needed
            return _truncate_context_to_budget(context, available_tokens)
    except Exception as e:
        logger.warning(f"SemanticContextBuilder failed: {e}. Falling back to simple concatenation.")

    # Fallback: simple chunk concatenation with token budgeting
    context_parts = []
    current_tokens = 0
    for chunk in chunks:
        text = chunk.get("chunk_text") or chunk.get("text") or ""
        if not text:
            continue
        section = chunk.get("section", "")
        part = text if not section else f"[{section.upper()}] {text}"
        part_tokens = _estimate_tokens(part) + 1
        if current_tokens + part_tokens > available_tokens:
            break
        context_parts.append(part)
        current_tokens += part_tokens

    if not context_parts and chunks:
        text = chunks[0].get("chunk_text") or chunks[0].get("text") or ""
        context_parts.append(_truncate_context_to_budget(text, available_tokens))

    return "\n\n".join(context_parts)

# ------------------------------------------------------------------------------
# Heuristic fallback (extractive)
# ------------------------------------------------------------------------------
def _heuristic_answer(query: str, chunks: List[Dict]) -> Tuple[str, str, str]:
    query_lower = query.lower()
    general_phrases = [
        "what is it about", "what is this document about", "what is this about",
        "summarize", "summary", "give me a summary", "what does it talk about",
        "what is this", "tell me about this", "what is the document about",
        "what is the file about", "summarize this document", "summarize this file"
    ]
    is_general = any(phrase in query_lower for phrase in general_phrases)
    stopwords = {
        "what", "is", "the", "does", "has", "completed", "candidate", "have", "listed", "about",
        "role", "at", "in", "of", "and", "a", "an", "to", "for", "on", "with", "by", "from", "are",
        "who", "which", "where", "how", "did", "do", "done", "this", "that", "these", "those"
    }
    query_tokens = re.findall(r"\b\w{3,}\b", query_lower)
    keywords = [kw for kw in query_tokens if kw not in stopwords]
    if not keywords:
        keywords = query_tokens
    sentences_pool = []
    seen = set()
    for idx, chunk in enumerate(chunks):
        text = chunk.get("chunk_text") or chunk.get("text") or ""
        text = text.replace("\u2013", " — ").replace("\u2014", " — ").replace("\u2022", " ").replace("\x95", " ")
        text = re.sub(r"\s+", " ", text).strip()
        sentences = re.split(r"(?<=[.!?])\s+", text)
        for s in sentences:
            s_clean = s.strip()
            if len(s_clean) > 15:
                s_lower = s_clean.lower()
                if s_lower not in seen:
                    seen.add(s_lower)
                    unique_matches = sum(1 for kw in keywords if kw in s_lower)
                    total_occurrences = sum(s_lower.count(kw) for kw in keywords)
                    chunk_weight = 10.0 / (idx + 1)
                    score = (unique_matches * 5.0 + total_occurrences * 0.5 + 1.0) * chunk_weight
                    sentences_pool.append((score, s_clean))
    sentences_pool.sort(key=lambda x: x[0], reverse=True)
    top_n = 6 if is_general else 4
    selected = [s for _, s in sentences_pool[:top_n]]
    if not selected:
        return "No sufficiently relevant context was found for this query.", "Local Heuristic Synthesizer", "404 Empty"
    return " ".join(selected), "Local Heuristic Synthesizer", "200 OK (Heuristic)"

# ------------------------------------------------------------------------------
# Main public API
# ------------------------------------------------------------------------------
def generate_answer(query: str, chunks: List[Dict[str, Any]]) -> Tuple[str, str, str]:
    """
    Generates a synthesized answer for the given query and chunks.
    Returns: (answer_text, provider_used, response_status)
    """
    if not chunks:
        return "No source chunks provided.", "None", "400 No Chunks"

    # 1. Build context with token budgeting (uses SemanticContextBuilder if available)
    context_text = _build_context(chunks, query)

    # 2. Build prompts
    system_prompt = (
        "You are a precise document Q&A assistant. Answer the user's question in 1-3 clear, natural sentences "
        "using ONLY the information from the provided sources.\n"
        "Strict Grounding Rules:\n"
        "1. Do NOT use external knowledge, infer, or extrapolate beyond the provided sources.\n"
        "2. Do NOT conflate or combine unrelated facts from different sources. For example, if one source mentions a scaling technique for outliers (like RobustScaler) and another mentions categorical encoding, do not assume or state that the scaling technique is a categorical encoder. Keep concepts strictly distinct.\n"
        "   Exception: You may synthesize and combine information across multiple retrieved sources when they represent elements of the same structured entity list (such as inventors, authors, applicants, contributors, references, table rows, or enumerated lists).\n"
        "3. Answer directly and concisely. Avoid bullet points or numbered lists unless explicitly presenting members of a structured list (e.g. inventors, authors, references).\n"
        "4. Do NOT copy-paste raw source text verbatim. Write a proper synthesized sentence.\n"
        "5. If the sources do not contain direct, explicit information to answer the question, or if you must guess, you MUST respond exactly: 'The document does not contain sufficient information to answer this question.'"
    )
    user_prompt = f"Sources:\n{context_text}\nQuestion: {query}\nProvide a direct, concise answer in 1-3 sentences:"

    # 3. Try providers in order
    for provider_name in LLM_PROVIDER_ORDER:
        provider = get_provider(provider_name)
        if provider is None:
            continue
        try:
            answer, _, _ = provider.generate(system_prompt, user_prompt)
            return answer, f"{provider.name} ({provider.model})", "200 OK"
        except Exception as e:
            logger.warning(f"Provider {provider_name} failed: {e}")
            continue

    # 4. Fallback to heuristic
    return _heuristic_answer(query, chunks)