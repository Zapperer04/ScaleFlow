# Deployment Architecture

ScaleFlow uses containerized deployments coordinated via Docker Compose.

## Service Connections
- **Port Mapping**:
  - `backend` API: `5000:5000`
  - `frontend` App: `3000:3000`
  - `redis` Broker: `6379:6379` (local mapping `6380:6380` or `6379`)
  - `postgres` Metadata DB: `5432:5432`
  - `qdrant` Vector DB: `6333:6333`
- **Volume Bindings**:
  - `./backend` mapped to `/app` for live coding and shared storage.
  - `./backend/storage` bound for uploads, local BM25 files, and graph databases.\n