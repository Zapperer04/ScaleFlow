import os
import logging
import math

logger = logging.getLogger(__name__)

_model = None

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

def get_embedding_model():
    global _model
    if _model is not None:
        return _model
        
    try:
        from sentence_transformers import SentenceTransformer
        # Disable huggingface warnings / download status bars if needed
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        logger.info(f"Attempting to load sentence-transformers model: {config.EMBEDDING_MODEL}")
        # Load model (downloads if not cached)
        _model = SentenceTransformer(config.EMBEDDING_MODEL)
        logger.info(f"Successfully loaded sentence-transformers model: {config.EMBEDDING_MODEL}")
    except Exception as e:
        logger.critical(f"CRITICAL: Failed to load sentence-transformers model: {e}")
        raise RuntimeError(f"Embedding model initialization failed: {e}") from e
        
    return _model

def embed_text(text: str) -> list[float]:
    model = get_embedding_model()
    try:
        # Generate embedding
        vector = model.encode(text, convert_to_numpy=True).tolist()
        return [round(float(v), 6) for v in vector]
    except Exception as e:
        logger.critical(f"CRITICAL: Error during model encoding: {e}")
        raise RuntimeError(f"Text embedding generation failed: {e}") from e

def embed_chunks(chunks: list[str]) -> list[list[float]]:
    return embed_chunks_with_progress(chunks)

def embed_chunks_with_progress(chunks: list[str], progress_callback=None) -> list[list[float]]:
    model = get_embedding_model()
    try:
        all_vectors = []
        batch_size = 64
        total_batches = math.ceil(len(chunks) / batch_size) if chunks else 0
        
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            vectors = model.encode(batch, convert_to_numpy=True).tolist()
            all_vectors.extend([[round(float(v), 6) for v in vector] for vector in vectors])
            
            if progress_callback:
                batch_num = (i // batch_size) + 1
                progress_callback(batch_num, total_batches, len(all_vectors), len(chunks))
                
        return all_vectors
    except Exception as e:
        logger.critical(f"CRITICAL: Error during model batch encoding: {e}")
        raise RuntimeError(f"Batch chunks embedding generation failed: {e}") from e
