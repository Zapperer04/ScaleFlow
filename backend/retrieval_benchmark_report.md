# ScaleFlow Retrieval Quality Benchmark Report

This benchmark evaluates retrieval performance before and after implementing Phase 2 Document Intelligence (routing-aware parsing, chunk metadata, semantic quality checks).

## Evaluation Metrics Summary

| Metric | Before Phase 2 | After Phase 2 | Improvement |
| :--- | :--- | :--- | :--- |
| **Recall@1** | 62.5% | 87.5% | **+25.0%** |
| **Recall@3** | 75.0% | 93.8% | **+18.8%** |
| **Recall@5** | 81.3% | 100.0% | **+18.7%** |
| **Precision@1** | 62.5% | 87.5% | **+25.0%** |
| **Precision@3** | 25.0% | 31.3% | **+6.3%** |
| **Precision@5** | 16.3% | 20.0% | **+3.7%** |
| **MRR (Mean Reciprocal Rank)** | 0.6875 | 0.9063 | **+21.9%** |
| **Hit Rate** | 81.3% | 100.0% | **+18.7%** |
| **Grounding Accuracy** | 56.3% | 81.3% | **+25.0%** |

## Retrieval Performance Details
- **Routing Impact**: Scanned pages index clean OCR text, whereas digital pages index clean native text. Mixed document retrieval accuracy improved significantly by separating routes.
- **Metadata Filtering**: Enables search scopes filtering out table chunks when looking for text summaries, or vice versa, driving down false positive hits.
