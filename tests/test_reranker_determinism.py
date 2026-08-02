import pytest
from backend.reranker import Reranker

def test_reranker_sorting_determinism():
    reranker = Reranker()
    
    candidates = [
        {
            "chunk_id": "chunk_b",
            "text": "Alternative details on scheduler rules.",
            "sources": ["semantic"],
            "semantic_score": 0.85,
            "bm25_score": 0.0,
            "graph_score": 0.0,
            "graph_priority": 1.0,
            "score": 0.90
        },
        {
            "chunk_id": "chunk_a",
            "text": "Core scheduling engine details.",
            "sources": ["semantic", "bm25"],
            "semantic_score": 0.85,
            "bm25_score": 5.2,
            "graph_score": 0.0,
            "graph_priority": 1.0,
            "score": 0.90
        },
        {
            "chunk_id": "chunk_c",
            "text": "Unrelated paragraph info.",
            "sources": ["bm25"],
            "semantic_score": 0.0,
            "bm25_score": 1.1,
            "graph_score": 0.0,
            "graph_priority": 0.0,
            "score": 0.40
        }
    ]

    # Deterministic keys rule:
    # 1. score DESC (chunk_a and chunk_b have 0.90, chunk_c has 0.40)
    # 2. graph_priority DESC (chunk_a and chunk_b have 1.0, chunk_c has 0.0)
    # 3. semantic_score DESC (chunk_a and chunk_b have 0.85)
    # 4. bm25_score DESC (chunk_a has 5.2, chunk_b has 0.0) -> chunk_a must rank 1st, chunk_b 2nd
    # 5. chunk_id ASC
    
    # We sort multiple times and confirm it produces the exact same order
    for _ in range(10):
        # We pass a copy to avoid mutation side effects
        shuffled = list(candidates)
        # shuffle manually to show sort stability independent of input sequence
        shuffled[0], shuffled[1] = shuffled[1], shuffled[0]
        
        result = reranker.rerank_candidates("scheduling", shuffled)
        assert len(result) == 3
        assert result[0]["chunk_id"] == "chunk_a"
        assert result[1]["chunk_id"] == "chunk_b"
        assert result[2]["chunk_id"] == "chunk_c"
