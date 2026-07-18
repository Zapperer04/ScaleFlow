# Component Ownership Matrix

| Component | Owner | Used By | Depends On | Should Exist? |
| :--- | :--- | :--- | :--- | :--- |
| **`app.py`** | Infrastructure | Web Client | DB, Redis, worker.py | Yes (but split) |
| **`worker.py`** | Task Engine | Queue Daemon | Services, DB, registry | Yes |
| **`pdf_parser.py`** | Parser Team | Worker | VLM API, PyPDF | Yes |
| **`bm25_service.py`** | Search Team | Worker, API | Local disk storage | Yes |
| **`vector_store.py`** | Search Team | Worker, API | Qdrant DB | Yes |\n