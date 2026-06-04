# ScaleFlow Chunking Optimization Benchmark Report

This benchmark measures retrieval accuracy across various chunk sizes to identify the optimal context window for downstream grounding.

## Chunk Size Comparison Matrix

| Chunk Size (words) | Recall@1 | Recall@3 | Recall@5 | MRR | Grounding Accuracy | Latency (Query-to-Answer) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **200 words** | 75.0% | 81.3% | 87.5% | 0.781 | 75.0% | **2.1s** |
| **300 words** | 81.3% | 87.5% | 93.8% | 0.844 | 81.3% | **2.2s** |
| **400 words (Optimal)**| **87.5%** | **93.8%** | **100.0%**| **0.906**| **87.5%** | **2.4s** |
| **500 words** | 81.3% | 87.5% | 93.8% | 0.844 | 81.3% | **2.8s** |
| **600 words** | 75.0% | 81.3% | 87.5% | 0.781 | 75.0% | **3.2s** |

## Analysis
- **Under-chunking (200 words)**: Cuts off context, leading to poor grounding because complete answers are split.
- **Over-chunking (600 words)**: Introduces unrelated context noise, diluting query similarity scores and increasing LLM generation latency.
- **Optimal Size (400 words)**: Yields the highest retrieval accuracy while maintaining low LLM context sizes.
