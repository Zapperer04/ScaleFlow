# Retrieval Benchmark Report

## Overall Metrics Summary

- **recall_1**: 1.0000
- **recall_3**: 1.0000
- **recall_5**: 1.0000
- **recall_10**: 1.0000
- **precision_1**: 1.0000
- **precision_5**: 1.0000
- **mrr**: 1.0000
- **ndcg_5**: 1.0000
- **graph_coverage**: 1.0000
- **entity_coverage**: 1.0000
- **table_coverage**: 0.5714
- **context_recall**: 1.0000
- **context_precision**: 1.0000

## Comparative Expert configurations

| Config | Recall@5 | Precision@5 | MRR | NDCG@5 | Latency (s) |
| --- | --- | --- | --- | --- | --- |
| Vector-Only | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0003 |
| Graph-Only | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0003 |
| Entity-Only | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0001 |
| Table-Only | 0.1429 | 0.1429 | 0.1429 | 0.1429 | 0.0001 |
| Layout-Only | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0001 |
| Hybrid | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0008 |
