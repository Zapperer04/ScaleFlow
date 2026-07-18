# Risk Register

| Risk | Impact | Likelihood | Severity | Affected Module | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Monolith API Failure** | High | Medium | High | `app.py` | Any syntax error or database locking in `app.py` halts the entire pipeline API. |
| **Lease Expiry False Positive** | Medium | Medium | Medium | `worker.py` | Heavy CPU tasks block the event loop, causing workers to miss a lease renew window. |
| **External API Throttling** | High | High | High | `vlm_provider.py` | VLM parsers rely heavily on Gemini/OpenRouter; key exhaustion completely stalls VLM fallback stages. |
| **In-Memory Cache Pollution** | Medium | Low | Low | `embedding_service` | Thread-unsafe token buffers and HuggingFace pipelines can leak memory under sustained concurrency. |
| **Local File Index Loss** | High | Low | Medium | `bm25_service` | Shared BM25 indexes written to local storage will not persist across container scale-outs unless mounted on NFS. |\n