# API Endpoint Documentation (MR-RAG v1.0)

Every request to the serving platform requires API Key verification using the `X-API-Key` header.

---

## 1. Document Management APIs

### POST `/files/upload`
Uploads a document (PDF/TXT) and creates an ingestion pipeline.
- **Headers**:
  - `X-API-Key`: `your_secret_key`
- **Request Form-Data**:
  - `file`: Binary file data.
  - `pipeline_type`: Ingestion DAG type (e.g. `document_processing_demo`).
- **Response Example (201 Created)**:
  ```json
  {
    "pipeline_id": 4,
    "file_id": 18,
    "status": "created",
    "filename": "18_sample.pdf"
  }
  ```

---

## 2. Query & Retrieval APIs

### POST `/query-pipelines`
Submits a query request to run retrieval and synthesis.
- **Headers**:
  - `X-API-Key`: `your_secret_key`
  - `Content-Type`: `application/json`
- **Request JSON Payload**:
  ```json
  {
    "query": "Who is Kaustav Kumar?",
    "top_k": 5,
    "stream": false
  }
  ```
- **Response Example (201 Created)**:
  ```json
  {
    "pipeline_id": 29,
    "status": "created"
  }
  ```

### GET `/query-pipelines/{id}/answer`
Fetches the processed answer and retrieved contexts for a query pipeline.
- **Response Example (200 OK)**:
  ```json
  {
    "pipeline_id": 29,
    "status": "completed",
    "final_answer": {
      "answer": "Mr. Kaustav Kumar is a software engineer who built ScaleFlow.",
      "confidence": 0.96,
      "citations": [
        {
          "chunk_id": "chunk_p1_n17",
          "source_uri": "storage/uploads/18_sample.pdf"
        }
      ]
    },
    "retrieved_context": {
      "results": [
        {
          "chunk_id": "chunk_p1_n17",
          "score": 0.945,
          "chunk_text": "Kaustav Kumar - Built ScaleFlow platform"
        }
      ]
    }
  }
  ```

---

## 3. Operations & Health APIs

### GET `/health`
Check service connection integrity (SQL, Redis, Qdrant).
- **Response Example (200 OK)**:
  ```json
  {
    "status": "healthy",
    "services": {
      "sqlite": "connected",
      "redis": "connected",
      "qdrant": "connected"
    }
  }
  ```

These endpoints verify that the platform remains **Production Qualified under the evaluated benchmark suite**.
