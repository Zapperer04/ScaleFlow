# Benchmark & Evaluation Methodology (MR-RAG v1.0)

This document details the scientific evaluation framework of the MR-RAG platform, including dataset domains, baseline configurations, metrics formulas, production gates, and regression testing.

## 1. Dataset Categories

Benchmarks evaluate retrieval quality across 7 distinct domain-specific categories to ensure high coverage:
1. **Books** (`billion_dollar_sure_thing.pdf`): Long-form narrative and logical reasoning tracking.
2. **Contracts** (`category_A_simple.pdf`): Strict legal clauses and attribute mapping.
3. **Manuals** (`category_B_academic.pdf`): Multi-column academic layouts and sections.
4. **Finance** (`synthetic_table.pdf`): Complex tables, cells, captions, and structural alignments.
5. **Forms** (`category_C_large.pdf`): Structured form documents and label-value pairs.
6. **Research** (`photographed_notes.pdf`): Hand-drawn or photographed document scans with noise.
7. **Mixed** (`category_D_scanned.pdf`): Multi-modal layouts containing a mixture of text, tables, and scanning noise.

---

## 2. Six Baseline Configurations

We compare system configurations using the `BaselineManager` to measure the contribution of each engine layer:
- **Vector-Only**: Employs `VectorExpert` alone for dense vector cosine similarity.
- **Graph-Only**: Employs `GraphExpert` alone for structural graph database traversal.
- **Hybrid**: Merges all parallel experts (`Vector`, `Graph`, `Entity`, `Table`, `Layout`) using Reciprocal Rank Fusion (RRF).
- **Hybrid + Reranker**: Hybrid retrieval followed by a Cross-Encoder Reranker.
- **Hybrid + Multi-Hop**: Hybrid + Reranker with secondary query analysis and keywords-based query expansion.
- **Hybrid + Reflection**: Hybrid + Reranker + generation with self-reflection validation (LLM retry loops).

---

## 3. Evaluation Metrics

### Recall@k
Measures the proportion of relevant chunks retrieved in the top $k$ candidates:
$$\text{Recall}@k = \frac{|\text{Retrieved}_k \cap \text{GroundTruth}|}{|\text{GroundTruth}|}$$

### Precision@k
Measures the proportion of retrieved chunks in the top $k$ that are relevant:
$$\text{Precision}@k = \frac{|\text{Retrieved}_k \cap \text{GroundTruth}|}{k}$$

### Mean Reciprocal Rank (MRR)
Evaluates position-based accuracy. Focuses on the rank of the first correct chunk:
$$\text{MRR} = \frac{1}{\min_{c \in \text{Retrieved}} \text{Rank}(c \text{ in GroundTruth})}$$

### Normalized Discounted Cumulative Gain (NDCG@k)
Measures retrieval relevance sorted order:
$$\text{NDCG}@k = \frac{\text{DCG}@k}{\text{IDCG}@k}$$
Where:
$$\text{DCG}@k = \sum_{i=1}^k \frac{2^{rel_i} - 1}{\log_2(i + 1)}$$

### Exact Match (EM) & F1 Score
Used for generated response evaluation against ground truth answers.

### Citation Accuracy
Measures the percentage of citations referencing valid source chunk IDs:
$$\text{Citation Accuracy} = \frac{\text{Citations pointing to valid chunks}}{\text{Total Citations}} \times 100$$

### Hallucination Rate & Classifications
Classifies generated claims into:
- **Unsupported**: Statements that cannot be linked to retrieved chunks.
- **Wrong number**: Mismatched dates, prices, or statistics.
- **Wrong entity**: Mismatched names or organizations.
- **Wrong citation**: Citations pointing to incorrect text.
- **Missing citation**: Claims made without attribution.
- **Fabricated table/graph**: Generating non-existent structure relationships.

---

## 4. Production Qualification Gates

The platform qualifies as **"Production Qualified under the evaluated benchmark suite"** only if all the following gates pass:
- `Recall@5` $\ge$ 0.90
- `MRR` $\ge$ 0.88
- `Citation Accuracy` $\ge$ 98%
- `Hallucination Rate` $\le$ 2%
- `P95 Retrieval Latency` $<$ 300ms
- `P95 Generation Latency` $<$ 2.5s
- `Cache Hit Ratio` $>$ 70%
- `Crash Recovery`: PASS
- `Restart Resilience`: PASS
- `Security Sanity`: PASS
