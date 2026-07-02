import os
import logging
import math
import time

logger = logging.getLogger(__name__)

_model = None
_model_load_time = 0.0

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

def get_embedding_model():
    global _model, _model_load_time
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
        logger.info(f"Successfully loaded sentence-transformers model: {config.EMBEDDING_MODEL} (took {_model_load_time:.4f}s)")
    except Exception as e:
        logger.critical(f"CRITICAL: Failed to load sentence-transformers model: {e}")
        raise RuntimeError(f"Embedding model initialization failed: {e}") from e
        
    return _model

def get_model_load_time() -> float:
    global _model_load_time
    return _model_load_time

# ------------------------------------------------------------------------------
# Graph‑native embedding text builder
# ------------------------------------------------------------------------------
def build_embedding_text(chunk: dict) -> str:
    """
    Construct a rich embedding representation from a graph chunk.
    Priority: 'embedding_text' field, then this builder, then 'text' field.
    """
    parts = []

    # Section hierarchy
    section = chunk.get("section", "")
    section_path = chunk.get("section_path", "")
    if section_path:
        parts.append(f"[SECTION] {section_path}")
    elif section and section != "unknown":
        parts.append(f"[SECTION] {section}")

    # Content type
    content_type = chunk.get("content_type", "")
    if content_type:
        parts.append(f"[TYPE] {content_type}")

    # Entities
    entities = chunk.get("entities", [])
    if entities:
        # Flatten entity values (list of dicts or strings)
        entity_strs = [e.get("value", str(e)) if isinstance(e, dict) else str(e) for e in entities]
        parts.append(f"[ENTITIES] {', '.join(entity_strs)}")

    # Keywords
    keywords = chunk.get("keywords", [])
    if keywords:
        parts.append(f"[KEYWORDS] {', '.join(keywords)}")

    # Main text content
    text = chunk.get("text", "")
    if text:
        parts.append(f"[CONTENT] {text}")

    # Cross references – robust handling of dict/list/other
    cross_refs = chunk.get("cross_refs", [])
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

    # Importance score – include if >0 to guide embeddings
    importance = chunk.get("importance_score", 0.0)
    if importance > 0.0:
        parts.append(f"[IMPORTANCE] {round(importance, 2)}")

    return "\n".join(parts)


def embed_text(text: str) -> list[float]:
    model = get_embedding_model()
    try:
        # Generate embedding
        vector = model.encode(text, convert_to_numpy=True).tolist()
        return [round(float(v), 6) for v in vector]
    except Exception as e:
        logger.critical(f"CRITICAL: Error during model encoding: {e}")
        raise RuntimeError(f"Text embedding generation failed: {e}") from e


def embed_chunks(chunks: list) -> list[list[float]]:
    return embed_chunks_with_progress(chunks)


def embed_chunks_with_progress(chunks: list, progress_callback=None, batch_size=None) -> list[list[float]]:
    model = get_embedding_model()
    if batch_size is None:
        batch_size = config.EMBEDDING_BATCH_SIZE

    # Prepare a list of texts from the chunks (accepts both strings and graph-native dicts)
    texts = []
    for chunk in chunks:
        if isinstance(chunk, dict):
            # Graph‑native chunk: use embedding_text, build_embedding_text, or text
            emb_text = chunk.get("embedding_text")
            if not emb_text:
                emb_text = build_embedding_text(chunk)
            if not emb_text:
                emb_text = chunk.get("text", "")
            texts.append(emb_text)
        elif isinstance(chunk, str):
            # Legacy plain string
            texts.append(chunk)
        else:
            # Fallback to string conversion
            texts.append(str(chunk))

    try:
        all_vectors = []
        total_batches = math.ceil(len(texts) / batch_size) if texts else 0
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            # Use numpy-native tolist() directly without slow per-element float rounding loops
            vectors = model.encode(batch, batch_size=len(batch), convert_to_numpy=True).tolist()
            all_vectors.extend(vectors)
            
            if progress_callback:
                batch_num = (i // batch_size) + 1
                progress_callback(batch_num, total_batches, len(all_vectors), len(chunks))
            
            # Yield control back to Python's GIL to allow heartbeat and lease renewer threads to run
            time.sleep(0.1)
                
        return all_vectors
    except Exception as e:
        logger.critical(f"CRITICAL: Error during model batch encoding: {e}")
        raise RuntimeError(f"Batch chunks embedding generation failed: {e}") from e