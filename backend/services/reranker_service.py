"""
reranker_service.py — Cross‑encoder reranking for ScaleFlow.

Thread‑safe, device‑aware, production‑ready cross‑encoder reranking.
"""

import copy
import logging
import math
import os
import threading
import time
from typing import List, Dict, Any, Optional

import torch
from sentence_transformers import CrossEncoder

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# Configuration with fallbacks
# ------------------------------------------------------------------------------
RERANK_MODEL = getattr(config, "RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
RERANK_BATCH_SIZE = getattr(config, "RERANK_BATCH_SIZE", 16)
RERANK_MAX_LENGTH = getattr(config, "RERANK_MAX_LENGTH", 512)
RERANK_USE_FP16 = getattr(config, "RERANK_USE_FP16", False)  # disabled by default
RERANK_USE_QUANTIZATION = getattr(config, "RERANK_USE_QUANTIZATION", False)

# ------------------------------------------------------------------------------
# Thread‑safe singleton
# ------------------------------------------------------------------------------
_model: Optional[CrossEncoder] = None
_model_lock = threading.Lock()
_device: Optional[str] = None
_model_loaded = False

def _select_device() -> str:
    """Select best available device."""
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch, "mps") and torch.mps.is_available():
        return "mps"
    return "cpu"

def _load_model() -> CrossEncoder:
    """Load the cross‑encoder model with appropriate device and options."""
    global _device
    _device = _select_device()
    logger.info(f"[RERANKER] Selected device: {_device}")

    # Load model
    model = CrossEncoder(
        RERANK_MODEL,
        device=_device,
        max_length=RERANK_MAX_LENGTH,
        default_activation_function=None,  # we apply sigmoid manually
        num_labels=1,
    )

    # Optional CPU quantization (experimental)
    if _device == "cpu" and RERANK_USE_QUANTIZATION:
        try:
            import torch.quantization
            model.model = torch.quantization.quantize_dynamic(
                model.model, {torch.nn.Linear}, dtype=torch.qint8
            )
            logger.info("[RERANKER] Applied dynamic quantization")
        except Exception as e:
            logger.warning(f"[RERANKER] Quantization failed: {e}")

    # Warm‑up inference (initialize kernels, eliminate first‑request latency)
    try:
        dummy_query = "warmup"
        dummy_text = "warmup text"
        with torch.inference_mode():
            model.predict([[dummy_query, dummy_text]], batch_size=1)
        logger.info("[RERANKER] Warm‑up inference completed")
    except Exception as e:
        logger.warning(f"[RERANKER] Warm‑up failed: {e}")

    return model

def get_reranker() -> CrossEncoder:
    """Thread‑safe singleton getter."""
    global _model, _model_loaded
    if _model_loaded and _model is not None:
        return _model

    with _model_lock:
        if _model_loaded and _model is not None:
            return _model
        _model = _load_model()
        _model_loaded = True
        logger.info(f"[RERANKER] Model loaded: {RERANK_MODEL}")
        return _model

# ------------------------------------------------------------------------------
# Reranking core
# ------------------------------------------------------------------------------
def rerank(
    query: str,
    chunks: List[Dict[str, Any]],
    top_k: int = 3
) -> List[Dict[str, Any]]:
    """
    Rerank a list of chunks using the cross‑encoder.

    Args:
        query: The search query string.
        chunks: List of chunk dicts. Must contain 'chunk_text' or 'text'.
        top_k: Number of top results to return.

    Returns:
        List of chunk dicts (shallow copies) with added fields:
            - rerank_score: sigmoid‑normalized score (0‑1)
            - score: same as rerank_score for compatibility
        Sorted descending by rerank_score.
        If reranking fails, returns the original chunks (sorted by existing score
        if available, otherwise in input order).
    """
    # ------------------------------------------------------------------------
    # 1. Input validation
    # ------------------------------------------------------------------------
    if not chunks:
        return []

    if not query or not query.strip():
        logger.warning("[RERANKER] Empty query – returning chunks unchanged")
        return _copy_and_preserve_order(chunks)

    # Filter out chunks that have no text
    valid_chunks = []
    invalid_indices = []
    for idx, chunk in enumerate(chunks):
        text = chunk.get("chunk_text") or chunk.get("text")
        if text and isinstance(text, str) and text.strip():
            valid_chunks.append((idx, chunk))
        else:
            invalid_indices.append(idx)

    if not valid_chunks:
        logger.warning("[RERANKER] No valid chunks with text – returning empty")
        return []

    # ------------------------------------------------------------------------
    # 2. Prepare pairs
    # ------------------------------------------------------------------------
    pairs = []
    chunk_order = []  # preserve original order for later
    for idx, chunk in valid_chunks:
        text = chunk.get("chunk_text") or chunk.get("text", "")
        section = chunk.get("section", "")
        if section and section != "unknown":
            text = f"[{section.upper()}] {text}"
        pairs.append([query, text])
        chunk_order.append(idx)

    # ------------------------------------------------------------------------
    # 3. Load model and predict
    # ------------------------------------------------------------------------
    model = get_reranker()
    batch_size = max(1, min(RERANK_BATCH_SIZE, len(pairs)))

    start_time = time.perf_counter()
    try:
        with torch.inference_mode():
            scores = model.predict(
                pairs,
                batch_size=batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
        if scores is None:
            raise RuntimeError("CrossEncoder.predict returned None")
        inference_time = time.perf_counter() - start_time
        logger.debug(f"[RERANKER] Inference: {len(pairs)} chunks in {inference_time*1000:.1f}ms")
    except Exception as e:
        logger.error(f"[RERANKER] Inference failed: {e}. Returning original ranking.")
        # Fallback: return original chunks sorted by existing score if possible
        return _fallback_sort(chunks)

    # ------------------------------------------------------------------------
    # 4. Normalize scores with sigmoid (clamped)
    # ------------------------------------------------------------------------
    scored_items = []
    for idx, score in zip(chunk_order, scores):
        raw_score = float(score)
        # Clamp to avoid overflow in exp
        raw_score = max(min(raw_score, 60.0), -60.0)
        sigmoid_score = 1.0 / (1.0 + math.exp(-raw_score))
        scored_items.append((idx, sigmoid_score))

    # ------------------------------------------------------------------------
    # 5. Build result list (shallow copies of original chunks with rerank fields)
    # ------------------------------------------------------------------------
    result_chunks = []
    for idx, sigmoid_score in scored_items:
        # Shallow copy is sufficient; we only add top‑level keys.
        chunk_copy = chunks[idx].copy()
        chunk_copy["rerank_score"] = sigmoid_score
        chunk_copy["score"] = sigmoid_score
        result_chunks.append(chunk_copy)

    # Also include invalid chunks (those without text) at the end with low score
    for idx in invalid_indices:
        chunk_copy = chunks[idx].copy()
        chunk_copy["rerank_score"] = 0.0
        chunk_copy["score"] = 0.0
        result_chunks.append(chunk_copy)

    # ------------------------------------------------------------------------
    # 6. Sort and truncate
    # ------------------------------------------------------------------------
    result_chunks.sort(key=lambda x: x["rerank_score"], reverse=True)
    final = result_chunks[:top_k]

    # Telemetry (DEBUG level for per‑request)
    logger.debug(
        f"[RERANKER] Query: '{query[:30]}...' {len(chunks)} chunks → "
        f"{len(final)} results (top_k={top_k})"
    )

    return final

def _fallback_sort(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Fallback: return chunks sorted by existing 'score' key if present,
    otherwise preserve input order.
    """
    # Shallow copy to avoid mutation
    copies = [c.copy() for c in chunks]
    # If any chunk has a 'score' field, we sort by it
    has_score = any(c.get("score") is not None for c in copies)
    if has_score:
        copies.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    return copies

def _copy_and_preserve_order(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return shallow copies of chunks with no rerank fields added."""
    return [c.copy() for c in chunks]