import os
import logging
import math
import time
import hashlib
import json
import threading
from typing import List, Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

_model = None
_model_load_time = 0.0
_embedding_dim = None
_tokenizer = None  # model's tokenizer for token‑based truncation

# Embedding cache (Redis + in‑memory fallback)
_embedding_cache = {}
_cache_lock = threading.Lock()
_redis_client = None
_REDIS_CACHE_TTL = 86400  # 24 hours

# Pre‑computed embedding texts cache (to avoid rebuilding for same chunks)
_embedding_text_cache = {}
_embedding_text_cache_lock = threading.Lock()
_EMBEDDING_TEXT_CACHE_MAX = 10000

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Default max token limit – will be overridden by tokenizer
DEFAULT_MAX_TOKENS = 8192  # safe upper bound

# ------------------------------------------------------------------------------
# Adaptive batch size helper
# ------------------------------------------------------------------------------
def _get_adaptive_batch_size() -> int:
    """
    Compute batch size dynamically based on available RAM and device.
    Returns a safe batch size (int) that fits within memory limits.
    """
    base = config.EMBEDDING_BATCH_SIZE
    try:
        import psutil
        import torch
        available_gb = psutil.virtual_memory().available / (1024**3)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        if device == "cuda":
            # GPU can handle larger batches, but we also check GPU memory
            try:
                gpu_mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                if gpu_mem > 8:
                    return min(base, 64)
                elif gpu_mem > 4:
                    return min(base, 32)
                else:
                    return min(base, 16)
            except:
                return min(base, 32)
        else:
            # CPU: more RAM means larger batches
            if available_gb > 16:
                return min(base, 32)
            elif available_gb > 8:
                return min(base, 16)
            else:
                return min(base, 8)
    except:
        return base

# ------------------------------------------------------------------------------
# Redis connection (shared with GeminiRateManager if possible)
# ------------------------------------------------------------------------------
def _get_redis_client():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", 6379))
        _redis_client = redis.Redis(host=host, port=port, decode_responses=True, socket_timeout=2)
        _redis_client.ping()
        logger.info("Embedding cache: Redis connected.")
        return _redis_client
    except Exception as e:
        logger.warning(f"Embedding cache: Redis unavailable, using in‑memory LRU. {e}")
        return None

def _cache_embedding(text_hash: str, vector: List[float]):
    """Store embedding in CacheStore or in-memory LRU.

    NOTE (Deferred DI): This module is a flat functional module, not a class.
    Constructor injection of the CacheStore is deferred to a future refactor
    that wraps this module in an EmbeddingService class.
    Until then, embedding cache writes fall through to the in-memory LRU.
    See: docs/architecture/adr/007_constructor_dependency_injection_only.md
    """
    global _embedding_cache
    # Fallback: in-memory LRU (simple bounded dict)
    with _cache_lock:
        _embedding_cache[text_hash] = vector
        if len(_embedding_cache) > 10000:
            # Remove oldest (simple pop)
            _embedding_cache.pop(next(iter(_embedding_cache)))

def _lookup_embedding(text_hash: str) -> Optional[List[float]]:
    """Lookup embedding in in-memory cache.

    NOTE (Deferred DI): CacheStore injection deferred — see _cache_embedding.
    """
    with _cache_lock:
        return _embedding_cache.get(text_hash)

# ------------------------------------------------------------------------------
# Model loader with tokenizer
# ------------------------------------------------------------------------------
def get_embedding_model():
    global _model, _model_load_time, _embedding_dim, _tokenizer
    if _model is not None:
        return _model

    try:
        import torch
        torch.set_num_threads(config.EMBEDDING_NUM_THREADS)
        logger.info(f"Set PyTorch threads to: {config.EMBEDDING_NUM_THREADS}")

        from sentence_transformers import SentenceTransformer
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        logger.info(f"Loading model: {config.EMBEDDING_MODEL}")
        t_start = time.perf_counter()
        model = SentenceTransformer(config.EMBEDDING_MODEL)
        # Store tokenizer for truncation
        _tokenizer = model.tokenizer

        if config.EMBEDDING_QUANTIZATION:
            logger.info("Applying dynamic quantization...")
            import torch.nn as nn
            auto_model = model[0].auto_model
            quantized = torch.quantization.quantize_dynamic(auto_model, {nn.Linear}, dtype=torch.qint8)
            model[0].auto_model = quantized
            logger.info("Quantization applied.")

        _model = model
        _model_load_time = time.perf_counter() - t_start
        _embedding_dim = model.get_sentence_embedding_dimension()
        logger.info(f"Model loaded ({_model_load_time:.4f}s), dim={_embedding_dim}")
    except Exception as e:
        logger.critical(f"Failed to load embedding model: {e}")
        raise RuntimeError(f"Embedding model initialization failed: {e}") from e

    return _model

def get_model_load_time() -> float:
    return _model_load_time

def get_embedding_dimension() -> int:
    global _embedding_dim
    if _embedding_dim is None:
        get_embedding_model()
    return _embedding_dim

# ------------------------------------------------------------------------------
# Enhanced embedding text builder
# ------------------------------------------------------------------------------
def build_embedding_text(chunk: Dict[str, Any]) -> str:
    """
    Construct a rich embedding representation with:
      - Heading path repeated twice (for better weighting)
      - Table headers included
      - Figure captions, alt text, and surrounding heading included
      - Entities, keywords, content type
    Returns a string ready for embedding.
    """
    meta = chunk.get("metadata", chunk)
    parts = []

    # ---- 1. Heading hierarchy (repeated) ----
    heading_path = meta.get("heading_path") or chunk.get("heading_path")
    if heading_path and isinstance(heading_path, list) and heading_path:
        section_str = " > ".join(heading_path)
        # Repeat the section hierarchy twice to give it more weight
        parts.append(f"[SECTION] {section_str}")
        parts.append(f"[SECTION] {section_str}")
    else:
        # fallback to flat section
        section = meta.get("section") or chunk.get("section")
        section_path = meta.get("section_path") or chunk.get("section_path")
        if section_path:
            parts.append(f"[SECTION] {section_path}")
            parts.append(f"[SECTION] {section_path}")
        elif section and section != "unknown":
            parts.append(f"[SECTION] {section}")
            parts.append(f"[SECTION] {section}")

    # ---- 2. Structural type / category ----
    structural_type = meta.get("structural_type") or chunk.get("structural_type")
    content_type = meta.get("content_type") or chunk.get("content_type")
    chunk_type = structural_type or content_type or ""
    semantic_category = meta.get("semantic_category") or chunk.get("semantic_category")
    if semantic_category and semantic_category != "unknown":
        parts.append(f"[CATEGORY] {semantic_category}")

    # ---- 3. Entities (sorted, deduped) ----
    entities = meta.get("entities") or chunk.get("entities", [])
    if entities:
        entity_strs = []
        for e in entities:
            if isinstance(e, dict):
                val = e.get("value", str(e))
            else:
                val = str(e)
            if val:
                entity_strs.append(val)
        if entity_strs:
            entity_strs = sorted(set(entity_strs))
            parts.append(f"[ENTITIES] {', '.join(entity_strs)}")

    # ---- 4. Keywords ----
    keywords = meta.get("keywords") or chunk.get("keywords", [])
    if keywords:
        keywords = sorted(set(keywords))
        parts.append(f"[KEYWORDS] {', '.join(keywords)}")

    # ---- 5. Table-specific enhancements ----
    if chunk_type == "table":
        # Include table headers as part of the text
        headers = meta.get("headers") or chunk.get("headers")
        if headers:
            if isinstance(headers, list):
                parts.append(f"[TABLE_HEADERS] {', '.join(headers)}")
            else:
                parts.append(f"[TABLE_HEADERS] {str(headers)}")
        # Also include caption if present
        caption = meta.get("caption") or chunk.get("caption")
        if caption:
            parts.append(f"[CAPTION] {caption}")

    # ---- 6. Figure-specific enhancements ----
    elif chunk_type == "figure":
        caption = meta.get("caption") or chunk.get("caption")
        alt_text = meta.get("alt_text") or chunk.get("alt_text")
        if caption:
            parts.append(f"[CAPTION] {caption}")
        if alt_text:
            parts.append(f"[ALT_TEXT] {alt_text}")
        # Include surrounding heading if available (already in heading_path)

    # ---- 7. Main content ----
    text = chunk.get("text", "")
    if text:
        parts.append(f"[CONTENT] {text}")

    # ---- 8. Cross‑references (if any) ----
    cross_refs = meta.get("cross_refs") or chunk.get("cross_refs", [])
    if cross_refs:
        if isinstance(cross_refs, dict):
            ref_summary = "; ".join(
                f"{k}: {', '.join(v) if isinstance(v, list) else v}"
                for k, v in cross_refs.items()
            )
        elif isinstance(cross_refs, list):
            ref_summary = ", ".join(map(str, cross_refs))
        else:
            ref_summary = str(cross_refs)
        if ref_summary:
            parts.append(f"[REFERENCES] {ref_summary}")

    # Join with newlines
    full_text = "\n".join(parts)
    return full_text


def get_embedding_text(chunk: Dict[str, Any]) -> str:
    """
    Return pre‑computed embedding text from cache or build and cache it.
    This avoids rebuilding the same embedding text for identical chunks.
    """
    # Use a stable key: we hash the chunk's metadata and text.
    # For simplicity, we use a hash of the chunk's text and heading_path etc.
    # More robust: use a deterministic serialisation of the chunk.
    # We'll use a simple approach: hash the "text" + heading_path + content_type + entities + keywords.
    meta = chunk.get("metadata", chunk)
    key_parts = [
        chunk.get("text", ""),
        str(meta.get("heading_path", [])),
        str(meta.get("structural_type", "")),
        str(meta.get("content_type", "")),
        str(meta.get("entities", [])),
        str(meta.get("keywords", [])),
        str(meta.get("caption", "")),
        str(meta.get("headers", [])),
        str(meta.get("alt_text", "")),
    ]
    key = hashlib.sha256("|".join(key_parts).encode()).hexdigest()

    with _embedding_text_cache_lock:
        if key in _embedding_text_cache:
            return _embedding_text_cache[key]

    # Build fresh
    emb_text = build_embedding_text(chunk)
    # Cache with LRU eviction
    with _embedding_text_cache_lock:
        _embedding_text_cache[key] = emb_text
        if len(_embedding_text_cache) > _EMBEDDING_TEXT_CACHE_MAX:
            # Remove oldest (pop first)
            _embedding_text_cache.pop(next(iter(_embedding_text_cache)))
    return emb_text

# ------------------------------------------------------------------------------
# Truncation using tokenizer (respects token limit)
# ------------------------------------------------------------------------------
def _truncate_to_token_limit(text: str, max_tokens: int = None) -> str:
    """Truncate text to max_tokens using the model's tokenizer if available."""
    global _tokenizer
    if max_tokens is None:
        max_tokens = DEFAULT_MAX_TOKENS
    if _tokenizer is None:
        get_embedding_model()  # ensures tokenizer is loaded
    if _tokenizer is None:
        # fallback to character truncation
        if len(text) > max_tokens * 4:  # rough estimate
            text = text[:max_tokens * 4] + "..."
        return text

    tokens = _tokenizer.encode(text, add_special_tokens=False)
    if len(tokens) <= max_tokens:
        return text
    # Truncate tokens and decode
    truncated_tokens = tokens[:max_tokens]
    truncated = _tokenizer.decode(truncated_tokens, skip_special_tokens=True)
    # Add ellipsis to indicate truncation
    return truncated + "..."

# ------------------------------------------------------------------------------
# Main embedding functions with cache and adaptive batching
# ------------------------------------------------------------------------------
def embed_text(text: str) -> List[float]:
    if not text or not text.strip():
        return []

    # Compute hash for caching
    text_hash = hashlib.sha256(text.encode()).hexdigest()
    cached = _lookup_embedding(text_hash)
    if cached is not None:
        return cached

    model = get_embedding_model()
    # Tokenizer-based truncation
    truncated = _truncate_to_token_limit(text)
    vector = model.encode(truncated, convert_to_numpy=True).tolist()
    vector = [round(float(v), 6) for v in vector]
    # Cache the result
    _cache_embedding(text_hash, vector)
    return vector


def embed_chunks(chunks: List[Any]) -> List[List[float]]:
    return embed_chunks_with_progress(chunks)


def embed_chunks_with_progress(
    chunks: List[Any],
    progress_callback=None,
    batch_size: Optional[int] = None
) -> List[List[float]]:
    """
    Embed a list of chunks. Each chunk can be a dict (graph chunk) or a string.
    Returns a list of vectors in the same order.
    Uses embedding cache, tokenizer truncation, and adaptive batch sizing.
    """
    model = get_embedding_model()
    if batch_size is None:
        batch_size = _get_adaptive_batch_size()
    dim = get_embedding_dimension()

    # Pre-allocate result with zero vectors
    result = [[0.0] * dim for _ in range(len(chunks))]

    # Prepare texts to embed, along with their hashes for cache lookup
    texts_to_embed = []
    positions = []
    skipped_positions = []

    for idx, chunk in enumerate(chunks):
        should_embed = True
        if isinstance(chunk, dict):
            if chunk.get("embed") is False:
                should_embed = False
            else:
                # Use pre‑computed embedding text if available
                emb_text = chunk.get("embedding_text")
                if not emb_text:
                    emb_text = get_embedding_text(chunk)  # uses cache
                if not emb_text or not emb_text.strip():
                    should_embed = False
        elif isinstance(chunk, str):
            emb_text = chunk
            if not emb_text or not emb_text.strip():
                should_embed = False
        else:
            emb_text = str(chunk)
            if not emb_text or not emb_text.strip():
                should_embed = False

        if should_embed:
            # Tokenizer-based truncation will happen inside embed_text
            texts_to_embed.append(emb_text)
            positions.append(idx)
        else:
            skipped_positions.append(idx)

    # Process texts with caching
    if texts_to_embed:
        total = len(texts_to_embed)
        encoded_so_far = 0
        # We can't easily batch with cache because each text may have different hash; but we can still batch encode.
        # We'll do batch encoding, but check cache for each.
        # To keep batching efficient, we'll pre-filter cache hits and miss list.
        # Implementation: for each text, check cache; if hit, place vector; else collect for batch encoding.
        # However, we can also just call embed_text in a loop, but that would not leverage batch encoding efficiency.
        # We'll do a hybrid: gather all texts that are not in cache, then encode them in batches.

        uncached_texts = []
        uncached_positions = []
        for idx, text in enumerate(texts_to_embed):
            text_hash = hashlib.sha256(text.encode()).hexdigest()
            vec = _lookup_embedding(text_hash)
            if vec is not None:
                result[positions[idx]] = vec
            else:
                uncached_texts.append(text)
                uncached_positions.append(idx)

        if uncached_texts:
            # Encode uncached texts in adaptive batches
            total_uncached = len(uncached_texts)
            for i in range(0, total_uncached, batch_size):
                batch_texts = uncached_texts[i:i+batch_size]
                # Truncate each text
                truncated_batch = [_truncate_to_token_limit(t) for t in batch_texts]
                vectors = model.encode(truncated_batch, batch_size=len(truncated_batch), convert_to_numpy=True).tolist()
                for j, vec in enumerate(vectors):
                    vec_rounded = [round(float(v), 6) for v in vec]
                    orig_idx = positions[uncached_positions[i+j]]
                    result[orig_idx] = vec_rounded
                    # Cache the vector
                    text_hash = hashlib.sha256(uncached_texts[i+j].encode()).hexdigest()
                    _cache_embedding(text_hash, vec_rounded)

                encoded_so_far += len(batch_texts)
                if progress_callback:
                    batch_num = (i // batch_size) + 1
                    total_batches = math.ceil(total_uncached / batch_size)
                    progress_callback(batch_num, total_batches, encoded_so_far, len(chunks))

                # Yield control gently to allow other threads
                time.sleep(0)  # just yield, no real delay

    if skipped_positions:
        logger.warning(f"Skipped embedding for {len(skipped_positions)} chunks (embed=False or empty text); inserted zero vectors.")

    return result


# ------------------------------------------------------------------------------
# Pre‑compute embedding texts for all chunks (optional utility)
# ------------------------------------------------------------------------------
def precompute_embedding_texts(chunks: List[Dict]) -> None:
    """
    For each chunk, compute and store its embedding_text in the chunk itself
    (or in the cache) so that subsequent embedding calls can reuse it.
    """
    for chunk in chunks:
        if isinstance(chunk, dict):
            # The get_embedding_text function already caches; we can just call it to pre‑compute.
            # We can also store it back into the chunk for immediate use.
            emb_text = get_embedding_text(chunk)
            # Optionally store in chunk (if not already) to avoid re‑hashing later
            if "embedding_text" not in chunk:
                chunk["embedding_text"] = emb_text