# Dead Code & Duplicate Report

- **Duplicate Preprocessor File**: Root level `document_preprocessor.py` is identical to `backend/services/document_preprocessor.py` but is unreferenced in container tasks.
- **Unused Task Handlers**: `process_video` and `generate_report` are registered in `task_registry.py` but have no active production pipelines.
- **Stale Configs**: `PREPROCESS_HW_SCORE_MIN` is defined but handwriting validation remains non-blocking.\n