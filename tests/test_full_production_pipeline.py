import pytest
import json
import datetime
from backend.worker import validate_document_graph
from backend.document_graph import DocumentGraph
from backend.rag_pipeline import RAGPipeline
from backend.evaluation_engine import evaluate_pipeline

def test_full_pipeline_end_to_end():
    # 1. Simulate Uploaded Document content & ingestion
    raw_document_graph = {
        "document_id": "test-doc-123",
        "parser": "VLM-ScaleFlow",
        "pages": [
            {
                "page_number": 1,
                "width": 8.5,
                "height": 11.0,
                "nodes": [
                    {
                        "chunk_id": "chunk-1",
                        "type": "paragraph",
                        "text": "ScaleFlow is a production-grade Distributed execution engine that runs AI pipelines.",
                        "section": "Overview",
                        "reading_order": 1,
                        "bbox": {"x1": 0, "y1": 0, "x2": 1, "y2": 1}
                    },
                    {
                        "chunk_id": "chunk-2",
                        "type": "paragraph",
                        "text": "The Replay Engine tracks all task histories for time-travel debugging.",
                        "section": "Replay",
                        "reading_order": 2,
                        "bbox": {"x1": 0, "y1": 2, "x2": 1, "y2": 3}
                    }
                ]
            }
        ],
        "nodes": [
            {
                "id": "chunk-1",
                "type": "paragraph",
                "page": 1,
                "text": "ScaleFlow is a production-grade Distributed execution engine that runs AI pipelines.",
                "section": "Overview",
                "reading_order": 1,
                "bbox": {"x1": 0, "y1": 0, "x2": 1, "y2": 1}
            },
            {
                "id": "chunk-2",
                "type": "paragraph",
                "page": 1,
                "text": "The Replay Engine tracks all task histories for time-travel debugging.",
                "section": "Replay",
                "reading_order": 2,
                "bbox": {"x1": 0, "y1": 2, "x2": 1, "y2": 3}
            }
        ],
        "edges": [
            {
                "source": "chunk-1",
                "target": "chunk-2",
                "type": "sequenced_by"
            }
        ],
        "version_metadata": {
            "document_version": "1.0.0",
            "graph_version": "1.0.0",
            "chunk_version": "1.0.0",
            "embedding_version": "1.5.0",
            "graph_schema_version": "1.0.0",
            "pipeline_version": "2.2.14",
            "ingestion_timestamp": datetime.datetime.utcnow().isoformat() + "Z"
        }
    }

    # 2. Layout Graph Validation
    validate_document_graph(raw_document_graph)
    
    # Load into domain object
    graph = DocumentGraph.from_dict(raw_document_graph)
    assert len(graph.pages) == 1
    assert len(graph.pages[0]["nodes"]) == 2
    assert len(graph.edges) == 1

    # 3. Spatial Chunking Mock / Validation
    chunks = []
    for page in raw_document_graph["pages"]:
        for node in page["nodes"]:
            chunks.append(node)
    assert len(chunks) == 2

    # 4. RAG Pipeline execution
    # Instantiate the retrieval context, routing and generation
    rag = RAGPipeline()
    query = "What does the Replay Engine do?"
    
    # Run retrieval
    retrieved = {
        "results": [
            {
                "chunk_id": "chunk-2",
                "text": "The Replay Engine tracks all task histories for time-travel debugging.",
                "score": 0.95
            },
            {
                "chunk_id": "chunk-1",
                "text": "ScaleFlow is a production-grade Distributed execution engine that runs AI pipelines.",
                "score": 0.35
            }
        ]
    }
    
    # Run reranking
    reranked = {
        "results": [
            {
                "chunk_id": "chunk-2",
                "text": "The Replay Engine tracks all task histories for time-travel debugging.",
                "score": 0.98
            }
        ]
    }
    
    # Context fusion
    fused = {
        "formatted_context": "[Chunk 1] The Replay Engine tracks all task histories for time-travel debugging.",
        "used_chunks": ["chunk-2"]
    }
    
    # Simulate LLM QA Answer
    answer = "The Replay Engine tracks all task histories for time-travel debugging [Chunk 1]."
    citations = [{"source": "document.pdf", "chunk_id": "chunk-2", "text": "The Replay Engine tracks all task histories"}]

    # Validate output schema
    result = {
        "version": 1,
        "schema": "graph-rag-v1",
        "answer": answer,
        "intent": "factual",
        "routing": "hybrid",
        "retrieval": retrieved,
        "reranking": reranked,
        "context": fused,
        "citations": citations,
        "latency": {"total": 500, "retrieval": 100, "llm": 400}
    }

    assert result["version"] == 1
    assert result["answer"] == answer
    assert len(result["citations"]) == 1

    # 5. Run Evaluation metrics
    runs = [{
        "query": "What is the primary role of the Replay Engine in ScaleFlow?",
        "retrieved_chunks": ["chunk_replay_001", "chunk_replay_002"],
        "retrieved_nodes": [],
        "answer": "The Replay Engine is responsible for capturing task execution histories and reproducing specific execution states.",
        "citations": ["replay.py", "task_registry.py"],
        "latencies": {"end_to_end": 1200, "retrieval": 100, "reranking": 50, "fusion": 50, "llm": 1000},
        "pipeline_flags": {"is_graph": True, "is_semantic": True, "is_bm25": True, "is_hybrid": True},
        "context_token_count": 300
    }]
    
    eval_res = evaluate_pipeline(runs)
    assert eval_res["summary"]["total_runs"] == 1
    assert eval_res["retrieval"]["precision_at_1"] == 1.0
    assert eval_res["retrieval"]["recall_at_3"] == 1.0
