import pytest
from backend.evaluation_engine import evaluate_pipeline

def test_evaluate_pipeline_basic():
    # Mock some run reports matching benchmark queries
    runs = [
        {
            "query": "What is the primary role of the Replay Engine in ScaleFlow?",
            "retrieved_chunks": ["chunk_replay_001", "chunk_replay_002"],
            "retrieved_nodes": [],
            "answer": "The Replay Engine is responsible for capturing task execution histories and reproducing specific execution states.",
            "citations": ["replay.py", "task_registry.py"],
            "latencies": {
                "end_to_end": 1500,
                "retrieval": 150,
                "reranking": 50,
                "fusion": 50,
                "llm": 1250
            },
            "pipeline_flags": {
                "is_graph": True,
                "is_semantic": True,
                "is_bm25": True,
                "is_hybrid": True
            },
            "context_token_count": 500
        }
    ]
    
    result = evaluate_pipeline(runs)
    
    assert "summary" in result
    assert "retrieval" in result
    assert "generation" in result
    assert "performance" in result
    assert "pipeline" in result
    
    # Check retrieval metrics
    assert result["retrieval"]["precision_at_1"] == 1.0
    assert result["retrieval"]["recall_at_1"] == 0.5
    assert result["retrieval"]["recall_at_3"] == 1.0
    assert result["retrieval"]["mrr"] == 1.0
    assert result["retrieval"]["ndcg"] > 0.0
    
    # Check generation and latencies
    assert result["generation"]["faithfulness"] > 0.0
    assert result["performance"]["end_to_end_ms"] == 1500.0
    assert result["pipeline"]["graph_retrieval_pct"] == 100.0
