# ScaleFlow Worker Resource Utilization Profile
**Generated:** 2026-06-02 15:21:58

This report profiles worker resource utilization (CPU, memory, wait time) across the test categories.

## Average Resource Utilization
| Category | Worker CPU | Worker RAM | Queue Wait Time | Ingestion Pipeline Total |
|---|---|---|---|---|
| A | 0.0% | 0.02% | 289.67s | 118.33s |
| B | 0.0% | 0.02% | 301.67s | 122.67s |
| C | 0.0% | 0.02333% | 534.00s | 207.00s |
| D | 0.0% | 0.02667% | 99.33s | 107.67s |
| E | 0.0% | 0.02667% | 74.33s | 98.67s |
| F | 0.0% | 0.02% | 587.00s | 225.67s |

## In-Depth Worker Diagnostics
1. **Is the worker busy or waiting on I/O?**
   - During text extraction (pdfplumber, pypdf), the worker process is CPU-bound on a single thread. During OCR (pytesseract), it runs subprocesses which consume substantial CPU resources.
   - During Qdrant upsert and Redis polling, it waits briefly on network/IPC I/O, though this is negligible in local SQLite/in-memory mode.
2. **Would adding more workers improve throughput?**
   - Yes, for concurrent ingestion streams. Multiple workers would process distinct documents in parallel.
3. **Would additional workers improve single-document latency?**
   - No. Ingestion tasks within a single pipeline are sequential (parse -> validate -> chunk -> embed). A single document is processed sequentially, so more workers will not speed up a single pipeline.