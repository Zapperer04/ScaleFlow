# Reproducibility Manifest (MR-RAG v1.0)

This manifest outlines the parameters, datasets, and environment details required to reproduce the validation and benchmarking runs of the MR-RAG platform.

## System Configuration

### Hardware Specifications
- **CPU Profile**: ARM64 / x86_64 multi-core processor (minimum 4 cores recommended)
- **Memory Requirements**: Minimum 16 GB RAM (32 GB recommended for large scales)
- **Storage Profile**: SSD with >= 50 GB free space (Disk I/O speeds affect document builder pipeline times)
- **GPU Accelerator**: Optional (CUDA / MPS supported for embedding models and VLM transcription speedups)

### Software & Dependency Registry
- **Runtime Environment**: Python v3.10+
- **Database Servers**:
  - Redis v6.2+ (Task scheduling & distributed locks)
  - Qdrant v1.1+ (Vector & payload database)
- **Hugging Face Model Cache**: Pre-cached models stored under `backend/hf_cache/` to ensure deterministic offline execution.

---

## Benchmark Parameters

### Reproducibility Seed
To ensure deterministic execution across all embedding, graph traversal, and tokenization steps:
```python
RANDOM_SEED = 42
```
All random samplers, dataset splits, and neural network decoders must be seeded with `42` before running the benchmark.

### Evaluated Model Suite
- **Embedding Model**: `all-MiniLM-L6-v2` (Dimension: 384, Sequence length: 256)
- **Cross-Encoder Reranker**: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- **Default LLM Provider**: Gemini 1.5 Flash (via OpenRouter or direct endpoint)
- **OCR Parser fallback**: Tesseract OCR engine v5.0+

---

## Datasets & Ground Truths

Benchmarks are executed against the document suites in `benchmark/datasets/` spanning these domains:
1. **Books**: Evaluated on *billion_dollar_sure_thing.pdf* (narrative tracking)
2. **Contracts**: Evaluated on *category_A_simple.pdf* (clause validation)
3. **Manuals**: Evaluated on *category_B_academic.pdf* (technical diagrams & structure)
4. **Finance**: Evaluated on *synthetic_table.pdf* (tabular layouts & cells)
5. **Forms**: Evaluated on *category_C_large.pdf* (bounding boxes & forms)
6. **Research**: Evaluated on *photographed_notes.pdf* (noisy scanned notes)
7. **Mixed**: Evaluated on *category_D_scanned.pdf* (combination of text, tables, and images)

Each directory contains a `questions.json` with ground truth queries, target chunk indices, expected graph entities, and tables.

---

## Execution Methodology

To reproduce the benchmark and profiling results, run:
```bash
# Set seed environment variable
export RANDOM_SEED=42

# Execute benchmark runners
backend/venv/bin/python benchmark/run_benchmark.py
backend/venv/bin/python benchmark/run_load_test.py
backend/venv/bin/python benchmark/run_scalability.py
backend/venv/bin/python benchmark/run_profiling.py
```

This will regenerate all metrics manifest JSON files in `benchmark/results/` and compile the Markdown qualification logs.
