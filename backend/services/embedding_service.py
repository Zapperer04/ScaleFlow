import os
import logging
import math
import time

logger = logging.getLogger(__name__)

_model = None
_model_load_time = 0.0
_embedding_dim = None

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Default max length for embedding text (character count, ~2000 tokens)
MAX_EMBEDDING_TEXT_LENGTH = getattr(config, 'MAX_EMBEDDING_TEXT_LENGTH', 8192)


def get_embedding_model():
    global _model, _model_load_time, _embedding_dim
    if _model is not None:
        return _model
        
    try:
        import torch
        # Configure threads before model load/inference
        torch.set_num_threads(config.EMBEDDING_NUM_THREADS)
        logger.info(f"Set PyTorch threads to: {config.EMBEDDING_NUM_THREADS}")

        from sentence_transformers import SentenceTransformer
        # Disable huggingface warnings / download status bars if needed
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        logger.info(f"Attempting to load sentence-transformers model: {config.EMBEDDING_MODEL}")
        t_start = time.perf_counter()
        # Load model (downloads if not cached)
        loaded_model = SentenceTransformer(config.EMBEDDING_MODEL)
        
        # Apply dynamic quantization if enabled
        if config.EMBEDDING_QUANTIZATION:
            logger.info("Applying eager-mode dynamic quantization to embedding model...")
            auto_model = loaded_model[0].auto_model
            import torch.nn as nn
            quantized_auto_model = torch.quantization.quantize_dynamic(
                auto_model, {nn.Linear}, dtype=torch.qint8
            )
            loaded_model[0].auto_model = quantized_auto_model
            logger.info("Dynamic quantization applied successfully!")

        _model = loaded_model
        _model_load_time = time.perf_counter() - t_start
        # Get embedding dimension
        _embedding_dim = loaded_model.get_sentence_embedding_dimension()
        logger.info(f"Successfully loaded sentence-transformers model: {config.EMBEDDING_MODEL} (took {_model_load_time:.4f}s)")
    except Exception as e:
        logger.critical(f"CRITICAL: Failed to load sentence-transformers model: {e}")
        raise RuntimeError(f"Embedding model initialization failed: {e}") from e
        
    return _model

def get_model_load_time() -> float:
    global _model_load_time
    return _model_load_time

def get_embedding_dimension() -> int:
    global _embedding_dim
    if _embedding_dim is None:
        get_embedding_model()
    return _embedding_dim

# ------------------------------------------------------------------------------
# Graph‑native embedding text builder (enhanced for new chunk structure)
# ------------------------------------------------------------------------------
def build_embedding_text(chunk: dict) -> str:
    """
    Construct a rich embedding representation from a graph chunk.
    Handles both new graph chunks (with 'metadata') and legacy flat chunks.
    Returns a string ready for embedding.
    """
    # Normalise: if chunk has 'metadata', use it; otherwise fallback to chunk itself
    meta = chunk.get("metadata", chunk)

    parts = []

    # --- Section hierarchy (heading_path) ---
    heading_path = meta.get("heading_path") or chunk.get("heading_path")
    if heading_path and isinstance(heading_path, list):
        # Build a hierarchical section string: "Chapter > Section > Subsection"
        section_str = " > ".join(heading_path)
        if section_str:
            parts.append(f"[SECTION] {section_str}")
    else:
        # Legacy: 'section' or 'section_path' flat
        section = meta.get("section") or chunk.get("section")
        section_path = meta.get("section_path") or chunk.get("section_path")
        if section_path:
            parts.append(f"[SECTION] {section_path}")
        elif section and section != "unknown":
            parts.append(f"[SECTION] {section}")

    # --- Content type / structural type ---
    structural_type = meta.get("structural_type") or chunk.get("structural_type")
    content_type = meta.get("content_type") or chunk.get("content_type")
    chunk_type = structural_type or content_type or ""

    # --- Semantic category (if available) ---
    semantic_category = meta.get("semantic_category") or chunk.get("semantic_category")
    if semantic_category and semantic_category != "unknown":
        parts.append(f"[CATEGORY] {semantic_category}")

    # --- Entities (sort for deterministic output) ---
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
            entity_strs = sorted(set(entity_strs))  # sort and deduplicate
            parts.append(f"[ENTITIES] {', '.join(entity_strs)}")

    # --- Keywords (sort for deterministic) ---
    keywords = meta.get("keywords") or chunk.get("keywords", [])
    if keywords:
        keywords = sorted(set(keywords))
        parts.append(f"[KEYWORDS] {', '.join(keywords)}")

    # --- Main text content ---
    text = chunk.get("text", "")
    if text:
        # Truncate text to avoid exceeding model limits
        if len(text) > MAX_EMBEDDING_TEXT_LENGTH:
            # Truncate at sentence boundary if possible, else character
            truncated = text[:MAX_EMBEDDING_TEXT_LENGTH]
            # Attempt to cut at last period, question mark, or exclamation
            for delim in ('. ', '? ', '! '):
                last = truncated.rfind(delim)
                if last > 0:
                    truncated = truncated[:last+1]
                    break
            text = truncated + "..."
        parts.append(f"[CONTENT] {text}")

    # --- Cross references (robust handling) ---
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

    # --- Layout type / figure/table specific (optional) ---
    if chunk_type in ('table', 'figure'):
        # For tables/figures, we may want to include caption or structure
        caption = meta.get("caption") or chunk.get("caption")
        if caption:
            parts.append(f"[CAPTION] {caption}")

    # --- Additional metadata: confidence (optional, not in embedding text) ---
    # We do NOT include confidence or importance scores in the embedding text
    # as they are better kept as metadata for ranking.

    return "\n".join(parts)


def embed_text(text: str) -> list[float]:
    if not text or not text.strip():
        return []
    model = get_embedding_model()
    try:
        # Truncate if too long
        if len(text) > MAX_EMBEDDING_TEXT_LENGTH:
            text = text[:MAX_EMBEDDING_TEXT_LENGTH] + "..."
        vector = model.encode(text, convert_to_numpy=True).tolist()
        return [round(float(v), 6) for v in vector]
    except Exception as e:
        logger.critical(f"CRITICAL: Error during model encoding: {e}")
        raise RuntimeError(f"Text embedding generation failed: {e}") from e


def embed_chunks(chunks: list) -> list[list[float]]:
    return embed_chunks_with_progress(chunks)


def embed_chunks_with_progress(chunks: list, progress_callback=None, batch_size=None) -> list[list[float]]:
    """
    Embed a list of chunks. Each chunk can be a dict (graph chunk) or a string.
    Returns a list of vectors in the same order as the input chunks.
    For chunks that should not be embedded (embed=False or empty text), a zero vector
    of the correct embedding dimension is returned to preserve order and avoid breaking
    downstream consumers that expect a vector for every input chunk.
    """
    model = get_embedding_model()
    if batch_size is None:
        batch_size = config.EMBEDDING_BATCH_SIZE

    # Get embedding dimension for zero vectors
    dim = get_embedding_dimension()

    # Prepare texts and track positions
    texts_to_embed = []
    positions = []
    skipped_positions = []

    for idx, chunk in enumerate(chunks):
        # Determine if we should embed this chunk
        should_embed = True
        if isinstance(chunk, dict):
            # Check 'embed' flag (if present and False, skip)
            if chunk.get("embed") is False:
                should_embed = False
            else:
                # Build embedding text
                emb_text = chunk.get("embedding_text")
                if not emb_text:
                    emb_text = build_embedding_text(chunk)
                if not emb_text:
                    emb_text = chunk.get("text", "")
                # Skip empty or whitespace-only texts
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
            # Truncate if necessary
            if len(emb_text) > MAX_EMBEDDING_TEXT_LENGTH:
                emb_text = emb_text[:MAX_EMBEDDING_TEXT_LENGTH] + "..."
            texts_to_embed.append(emb_text)
            positions.append(idx)
        else:
            skipped_positions.append(idx)

    # Pre-allocate result with independent zero vectors
    result = [[0.0] * dim for _ in range(len(chunks))]

    # Encode only the texts that should be embedded
    if texts_to_embed:
        total_batches = math.ceil(len(texts_to_embed) / batch_size)
        encoded_so_far = 0
        for i in range(0, len(texts_to_embed), batch_size):
            batch_texts = texts_to_embed[i:i + batch_size]
            vectors = model.encode(batch_texts, batch_size=len(batch_texts), convert_to_numpy=True).tolist()
            # Place vectors at their original positions
            for j, vec in enumerate(vectors):
                orig_idx = positions[i + j]
                result[orig_idx] = [round(float(v), 6) for v in vec]

            encoded_so_far += len(batch_texts)
            if progress_callback:
                batch_num = (i // batch_size) + 1
                # Callback signature: (batch_num, total_batches, encoded_so_far, total_chunks)
                # This is the original contract used by worker.py and other callers.
                progress_callback(batch_num, total_batches, encoded_so_far, len(chunks))

            # Yield control to allow other threads
            time.sleep(0.1)

    # Log warning for skipped chunks (only if any)
    if skipped_positions:
        logger.warning(f"Skipped embedding for {len(skipped_positions)} chunks due to embed=False or empty text; inserted zero vectors.")

    return result