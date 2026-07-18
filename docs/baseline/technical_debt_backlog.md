# Technical Debt Backlog & Roadmap

This backlog outlines the debt items discovered during the baseline phase to serve as our engineering roadmap.

| ID | Title | Description | Affected Files | Severity | Est. Effort | Priority | Recommended Stage |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **DEBT-01** | App Monolith Refactor | Split routing, state management, and database logic out of `app.py`. | [app.py](file:///Users/kaustavkumar/Kaustav/Projects/task-schedular/backend/app.py) | Critical | High | High | Stage 1 |
| **DEBT-02** | Consolidate Preprocessors | Remove root-level `document_preprocessor.py` duplicate. | [document_preprocessor.py](file:///Users/kaustavkumar/Kaustav/Projects/task-schedular/document_preprocessor.py), [document_preprocessor.py](file:///Users/kaustavkumar/Kaustav/Projects/task-schedular/backend/services/document_preprocessor.py) | High | Low | High | Stage 1 |
| **DEBT-03** | Decouple DB Imports | Remove inline environment parsing inside models and isolate DB init. | [models.py](file:///Users/kaustavkumar/Kaustav/Projects/task-schedular/backend/models.py) | Medium | Low | Medium | Stage 1 |
| **DEBT-04** | Global Singletons Isolation | Wrap HuggingFace and Gemini state managers in dependency injection. | [vlm_provider.py](file:///Users/kaustavkumar/Kaustav/Projects/task-schedular/backend/services/vlm_provider.py) | Medium | Medium | Medium | Stage 2 |
| **DEBT-05** | Shared BM25 Storage | Index serialization requires NFS or centralized service instead of local folder. | [bm25_service.py](file:///Users/kaustavkumar/Kaustav/Projects/task-schedular/backend/services/bm25_service.py) | High | Medium | High | Stage 2 |
