from sentence_transformers import CrossEncoder
import logging

logger = logging.getLogger(__name__)
_model = None

def get_reranker():
    global _model
    if _model is None:
        _model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        logger.info("[RERANKER] Loaded cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _model

import math

def rerank(query: str, chunks: list, top_k: int = 3) -> list:
    if not chunks:
        return []
    
    model = get_reranker()
    
    # Build ONE pair per chunk
    pairs = []
    for chunk in chunks:
        text = chunk.get("chunk_text") or chunk.get("text", "")
        section = chunk.get("section", "")
        if section and section != "unknown":
            text = f"[{section.upper()}] {text}"
        pairs.append([query, text])  # one pair per chunk
    
    # scores[i] corresponds to pairs[i] corresponds to chunks[i]
    scores = model.predict(pairs)
    
    for i, chunk in enumerate(chunks):
        raw_score = float(scores[i])
        # Sigmoid normalization to convert logits to [0, 1] range
        sigmoid_score = 1.0 / (1.0 + math.exp(-raw_score))
        chunk["rerank_score"] = sigmoid_score
        # Update the unified score key so downstream filters use the reranked score
        chunk["score"] = sigmoid_score
    
    return sorted(chunks, key=lambda x: x["rerank_score"], reverse=True)[:top_k]
