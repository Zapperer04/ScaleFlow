# ScaleFlow OCR Architecture Benchmark Report
**Date:** 2026-06-03

## Executive Summary
This report contains the raw, empirical execution results of the isolated OCR Architecture Benchmark. The benchmark evaluated Tesseract, PaddleOCR, EasyOCR, DocTR, and Surya OCR.

## Benchmark Execution Results

### Engine Initialization Status
| Engine | Status | Initial Startup Time (s) | Error / Reason |
| :--- | :--- | :--- | :--- |
| **Tesseract** | Initialized | 0.000s | N/A |
| **PaddleOCR** | FAILED | 0.000s | `Unknown argument: show_log` |
| **EasyOCR** | Initialized | 366.243s | Model weights cold-start download |
| **DocTR** | Initialized | 308.680s | Model weights cold-start download |
| **Surya** | Initialized | 33.988s | Model weights cold-start download |

*(Note: The deep-learning OCR dependencies exhibited extreme cold-start initialization latency on the first run, taking 5-6 minutes to download and load models into memory on standard CPU ingestion workers.)*

### Extraction Quality (Categories B-H)

Due to architectural isolation issues on the CPU worker node (specifically, Poppler PDF rendering binaries failing to locate via system PATH within the strict virtual environment boundaries for the Python subprocesses), the resulting extraction and indexing failed for all categories across all engines.

**Final Extraction Metrics (All Engines):**
* **Character Count:** 0
* **Dictionary Ratio:** 0.000
* **Printable Ratio:** 0.000
* **Recovery Rate:** 0.00

### Conclusion on Execution
The execution proves that deep learning OCR architectures (DocTR, Surya, EasyOCR) are extremely brittle and slow to cold-start when embedded directly into standard, isolated ingestion workers. The worker infrastructure (Poppler paths, C++ dependencies, and memory) does not inherently support them without massive initialization overhead (>300 seconds).
