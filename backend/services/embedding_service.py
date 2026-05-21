import os
import logging
import math

logger = logging.getLogger(__name__)

_model = None
_fallback_mode = False

def get_embedding_model():
    global _model, _fallback_mode
    if _model is not None:
        return _model, _fallback_mode
        
    try:
        from sentence_transformers import SentenceTransformer
        # Disable huggingface warnings / download status bars if needed
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        logger.info("Attempting to load sentence-transformers model: all-MiniLM-L6-v2")
        # Load model (downloads if not cached)
        _model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Successfully loaded sentence-transformers model: all-MiniLM-L6-v2")
        _fallback_mode = False
    except Exception as e:
        logger.warning(f"Failed to load sentence-transformers. Using deterministic local fallback: {e}")
        _model = None
        _fallback_mode = True
        
    return _model, _fallback_mode

def embed_text(text: str) -> list[float]:
    model, fallback = get_embedding_model()
    if fallback or model is None:
        return deterministic_fallback_embed(text)
    try:
        # Generate embedding
        vector = model.encode(text, convert_to_numpy=True).tolist()
        return [round(float(v), 6) for v in vector]
    except Exception as e:
        logger.warning(f"Error during model encoding: {e}. Falling back to deterministic embedding.")
        return deterministic_fallback_embed(text)

def embed_chunks(chunks: list[str]) -> list[list[float]]:
    model, fallback = get_embedding_model()
    if fallback or model is None:
        return [deterministic_fallback_embed(chunk) for chunk in chunks]
    try:
        vectors = model.encode(chunks, convert_to_numpy=True).tolist()
        return [[round(float(v), 6) for v in vector] for vector in vectors]
    except Exception as e:
        logger.warning(f"Error during model batch encoding: {e}. Falling back to deterministic embeddings.")
        return [deterministic_fallback_embed(chunk) for chunk in chunks]

def deterministic_fallback_embed(text: str) -> list[float]:
    vector = [0.0] * 384
    if not text:
        return vector
    
    # Calculate a simple deterministic seed based on text content
    h = 0
    for char in text:
        h = (h * 31 + ord(char)) & 0xFFFFFFFF
        
    for i in range(384):
        # Use a deterministic pseudo-random sequence
        val = math.sin(h + i * 0.1) * math.cos(len(text) + i * 0.23)
        vector[i] = val
        
    # Normalize to unit vector
    mag = math.sqrt(sum(v*v for v in vector))
    if mag > 1e-9:
        vector = [round(v / mag, 6) for v in vector]
    else:
        vector = [0.0] * 384
        vector[0] = 1.0
    return vector
