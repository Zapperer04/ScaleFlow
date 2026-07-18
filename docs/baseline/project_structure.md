# Project Structure Inventory

## Directory Trees
- `backend/`: Application server and processing worker container root.
  - `context/`: Runtime contexts and local persistence stores.
  - `orchestrator/`: DAG construction and task dependency solvers.
  - `services/`: Core business logic packages (embeddings, chunking, BM25, graph expansion).
  - `storage/`: Directory structure for local files, temporary nodes, and DB backups.
- `frontend/`: React components and UI code.
- `docs/`: User and technical documentation.
- `tests/`: System verification suites.\n