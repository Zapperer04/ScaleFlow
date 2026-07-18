# Module Responsibility Matrix

| Module | Core Responsibility | Violates SRP? | Notes |
| :--- | :--- | :--- | :--- |
| `app.py` | API Server, State machine, DB Operations, Routing | **YES** | God class/script handling too many domains. |
| `worker.py` | Thread runner, task processor, task leases | **YES** | Handles both transport leases and specific worker tasks. |
| `models.py` | DB schemas, mixins, custom compression classes | NO | Encapsulates ORM models cleanly. |
| `document_preprocessor.py` | Blur, contrast, noise check & enhancement | NO | Clean image processing domain scope. |
| `pdf_parser.py` | Text & layout extraction from PDFs | NO | Encapsulates PyPDF, PDFPlumber, VLM fallbacks. |
| `chunking_service.py` | Document graph chunk split | NO | Structured chunk creation. |
| `vector_store.py` | Qdrant indexing & connection | NO | Interface wrapper for Qdrant. |
| `gemini_rate_manager.py` | API throttling & fallback queues | NO | Throttles external REST dependencies. |\n