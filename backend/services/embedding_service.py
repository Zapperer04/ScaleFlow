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

def embed_chunks_with_progress(chunks: list[str], progress_callback=None, batch_size=None) -> list[list[float]]:
    model = get_embedding_model()
    if batch_size is None:
        batch_size = config.EMBEDDING_BATCH_SIZE
    try:
        all_vectors = []
        total_batches = math.ceil(len(chunks) / batch_size) if chunks else 0
        
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
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
