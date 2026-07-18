# Codebase Statistics

This report documents lines of code (LOC), complexity, and import footprints.

## Key Files Summary

| File Path | LOC | Classes | Functions | Complexity (Est) | Responsibilities |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `backend/app.py` | 5,425 | 0 | 100 | 767 | God-file API server handling routing, database queries, Task state machine, and REST interface. |
| `backend/worker.py` | 2,104 | 2 | 52 | 378 | Task queue polling, lease renewal loop, and task dispatching to individual services. |
| `backend/services/document_preprocessor.py` | 1,847 | 2 | 46 | 273 | Image preprocessing, handwriting score metrics, blur check, and image enhancement. |
| `backend/services/gemini_rate_manager.py` | 1,622 | 4 | 52 | 256 | API rate-limit management and tokens backoff queues. |
| `backend/services/pdf_parser.py` | 1,407 | 3 | 24 | 223 | Fallback layout parser using PyPDF, PDFPlumber, and VLM. |
| `backend/services/chunking_service.py` | 1,100 | 1 | 23 | 224 | Multi-stage document graph and raw text chunking. |
| `backend/services/event_sourcing_service.py` | 984 | 0 | 9 | 183 | Event store publisher and database state tracker. |
| `backend/models.py` | 755 | 20 | 16 | 55 | SQLAlchemy metadata definitions and schema bindings. |
| `backend/services/vector_store.py` | 688 | 1 | 13 | 94 | Qdrant multi-collection database connectivity. |
| `backend/config.py` | 158 | 0 | 1 | 28 | Configuration variable loading from env. |

## Highlights
- **God Files (over 5,000 LOC)**: `backend/app.py` (5,425 LOC).
- **God Files (over 1,000 LOC)**: `backend/worker.py`, `backend/services/document_preprocessor.py`, `backend/services/gemini_rate_manager.py`, `backend/services/pdf_parser.py`, `backend/services/chunking_service.py`.\n