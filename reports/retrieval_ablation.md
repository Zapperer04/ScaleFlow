# Retrieval Ablation Study

Comparison of different retrieval experts configuration:

| Expert Config | Recall@5 | Precision@5 | Latency (s) | Token Usage |
| --- | --- | --- | --- | --- |
| Vector-Only | 1.0000 | 1.0000 | 0.0003 | 16 |
| Graph-Only | 1.0000 | 1.0000 | 0.0004 | 16 |
| Entity-Only | 0.0000 | 0.0000 | 0.0002 | 0 |
| Table-Only | 1.0000 | 1.0000 | 0.0002 | 16 |
| Layout-Only | 0.0000 | 0.0000 | 0.0001 | 0 |
| Hybrid | 1.0000 | 1.0000 | 0.0009 | 16 |
