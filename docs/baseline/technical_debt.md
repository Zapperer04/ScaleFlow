# Technical Debt Inventory

- **App.py Monolith**: Handles routing, database updates, background checks, and utility validations. Over 5k lines of code.
- **Shared Worker Lease Logic**: The lease renewal is driven by HTTP POSTs inside a worker-owned thread `LeaseRenewer`. It is tightly coupled to HTTP responses and can cause workers to fail if network timeouts occur.
- **Embedded Database Models**: Environment loading and DB dialect selection are done globally inside `models.py` which can trigger unexpected side effects on import.
- **Global API Singletons**: Gemini API client states, HuggingFace sentence transformer pipelines, and rate managers are defined as static instances.
- **Duplicate Document Preprocessor**: The workspace includes both `document_preprocessor.py` (root level) and `backend/services/document_preprocessor.py`.\n