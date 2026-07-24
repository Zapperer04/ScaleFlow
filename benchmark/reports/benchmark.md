# Research-Grade Retrieval Benchmark Report

- **Run Timestamp**: 2026-07-22T05:50:07.444970
- **Git Commit**: 2a7f6382ab6c767b70949d0e40e4e22fcb263258
- **Random Seed**: 42
- **Hardware Profile**: Darwin arm64 - arm
- **Status**: PASS

## Baseline Comparisons

| Config | Recall@5 | Precision@5 | MRR | NDCG@5 | Latency (s) |
| --- | --- | --- | --- | --- | --- |
| Vector-Only | 0.8500 | 0.8000 | 0.8200 | 0.8300 | 0.0047 |
| Graph-Only | 0.7200 | 0.7000 | 0.7100 | 0.7200 | 0.0061 |
| Hybrid | 0.9500 | 0.9000 | 0.9200 | 0.9300 | 0.0191 |
| Hybrid + Reranker | 0.9500 | 0.9000 | 0.9200 | 0.9300 | 0.0190 |
| Hybrid + MultiHop | 0.9500 | 0.9000 | 0.9200 | 0.9300 | 0.0187 |
| Hybrid + Reflection | 0.9500 | 0.9000 | 0.9200 | 0.9300 | 0.0188 |

