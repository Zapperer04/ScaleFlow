import pytest
from backend.context_fusion import ContextFusion

def test_context_fusion_groups():
    fusion = ContextFusion(token_budget=100)
    
    candidates = [
        {
            "chunk_id": "chunk_1",
            "text": "Some general description details.",
            "semantic_score": 0.8,
            "bm25_score": 0.0,
            "graph_score": 0.0,
            "chunk": {"metadata": {"type": "paragraph"}}
        },
        {
            "chunk_id": "chunk_table",
            "text": "| data |",
            "semantic_score": 0.7,
            "bm25_score": 0.0,
            "graph_score": 0.0,
            "chunk": {"metadata": {"type": "table"}}
        }
    ]

    fused = fusion.fuse_context(candidates)
    
    assert len(fused.supporting_chunks) == 1
    assert len(fused.tables) == 1
    assert fused.tables[0]["chunk_id"] == "chunk_table"
    
    prompt = fused.to_prompt_string()
    assert "=== TABLES ===" in prompt
    assert "=== SUPPORTING EVIDENCE ===" in prompt
