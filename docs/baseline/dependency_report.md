# Dependency Report

This report analyzes import couplings, cyclic paths, and service architectures.

## Coupling Analysis

```mermaid
graph TD
    app.py --> config.py
    app.py --> models.py
    app.py --> worker.py
    worker.py --> task_registry.py
    worker.py --> services/document_preprocessor.py
    worker.py --> services/pdf_parser.py
    worker.py --> services/chunking_service.py
    worker.py --> services/embedding_service.py
    worker.py --> services/bm25_service.py
    services/vlm_provider.py --> services/gemini_rate_manager.py
    services/vlm_provider.py --> services/pdf_parser.py
```

## Identified Cyclic / Tight Couplings
- **`app.py` & `worker.py`**: Mutual dependencies on initialization pathways.
- **`services/vlm_provider.py` & `services/pdf_parser.py`**: Bidirectional logic around layout text/scans.
- **Global State**: Singletons in `vlm_provider`, `embedding_service`, and `gemini_rate_manager` retain API tokens and network sessions in global variables.\n