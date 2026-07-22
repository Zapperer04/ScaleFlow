# Latency Performance Analysis

Detailed runtime profiling across E2E stages:

### Query: What is the summary of row values in Table 1?
- **Total Time**: 0.0011s
- **Fusion Engine**: 0.0000s
- **Reranker**: 0.0000s
- **Context Optimizer**: 0.0000s
- **Experts**:
  - *vector*: 0.0004s
  - *entity*: 0.0004s
  - *table*: 0.0002s
  - *layout*: 0.0001s
  - *graph*: 0.0007s

### Query: Who is the primary founder of Google Corp?
- **Total Time**: 0.0008s
- **Fusion Engine**: 0.0000s
- **Reranker**: 0.0000s
- **Context Optimizer**: 0.0000s
- **Experts**:
  - *vector*: 0.0003s
  - *entity*: 0.0003s
  - *table*: 0.0003s
  - *layout*: 0.0001s
  - *graph*: 0.0006s

### Query: What is the content of the bottom right paragraph?
- **Total Time**: 0.0008s
- **Fusion Engine**: 0.0000s
- **Reranker**: 0.0000s
- **Context Optimizer**: 0.0000s
- **Experts**:
  - *entity*: 0.0002s
  - *table*: 0.0002s
  - *vector*: 0.0005s
  - *layout*: 0.0003s
  - *graph*: 0.0006s

### Query: Review the statistics in Table 1
- **Total Time**: 0.0009s
- **Fusion Engine**: 0.0000s
- **Reranker**: 0.0000s
- **Context Optimizer**: 0.0000s
- **Experts**:
  - *vector*: 0.0003s
  - *entity*: 0.0002s
  - *table*: 0.0001s
  - *layout*: 0.0002s
  - *graph*: 0.0006s

