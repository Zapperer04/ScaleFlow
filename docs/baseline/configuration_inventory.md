# Configuration Variables Inventory

| Variable | Default | Purpose | Required | Can Remove? |
| :--- | :--- | :--- | :--- | :--- |
| `DB_MODE` | `postgres` | SQL persistence selector | Yes | No |
| `DATABASE_URL` | `postgresql://...` | Connection URI for models | Yes | No |
| `REDIS_HOST` | `localhost` | Broker host | Yes | No |
| `EMBEDDING_MODEL` | `BAAI/bge-base-en-v1.5` | Dense vector generator model | Yes | No |
| `RERANKER_MODEL` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Scoring model | Yes | No |
| `PDF_LOW_TEXT_CHARS` | `20` | Threshold character length for digital extraction validation | Yes | No |\n