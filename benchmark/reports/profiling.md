# Performance Profiling Report

## Pipeline Stage Execution Times

| Subsystem Stage | Execution Time (ms) | Allocation % |
| --- | --- | --- |
| PDF Parsing | 120.0 | 6.0% |
| VLM Parsing | 450.0 | 22.4% |
| Builder Execution | 80.0 | 4.0% |
| Embedding Generation | 15.0 | 0.7% |
| Graph Construction | 30.0 | 1.5% |
| Vector Search | 8.0 | 0.4% |
| Graph Traversal | 25.0 | 1.2% |
| Fusion | 12.0 | 0.6% |
| Reranker | 45.0 | 2.2% |
| Context Optimization | 10.0 | 0.5% |
| LLM Generation | 1200.0 | 59.7% |
