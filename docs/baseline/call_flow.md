# Call Flow Sequence Diagrams

## Document Processing Sequence

```mermaid
sequenceDiagram
    participant User
    participant API
    participant DB
    participant Queue
    participant Worker
    
    User->>API: POST /files/upload
    API->>DB: Save FileRecord (status=uploaded)
    API->>DB: Create Pipeline & Tasks
    API->>Queue: Enqueue Task (preprocess_document)
    Queue-->>Worker: Dequeue Task
    Worker->>Worker: Preprocess Document
    Worker->>API: PATCH /tasks/{id} (status=completed)
    API->>Queue: Enqueue Next Task (parse_document)
    Queue-->>Worker: Dequeue Task
    Worker->>Worker: VLM/OCR Parse
    Worker->>API: PATCH /tasks/{id} (status=completed)
```

## Query & Retrieval Sequence

```mermaid
sequenceDiagram
    participant User
    participant API
    participant VectorStore
    participant Reranker
    
    User->>API: POST /search
    API->>VectorStore: Search Dense Embeddings
    API->>API: Local BM25 Search
    API->>API: Merge Dense + Sparse Scores
    API->>API: Graph Expansion (find neighbors)
    API->>Reranker: Cross-Encoder Score
    Reranker-->>API: Reranked list
    API-->>User: Search Results
```\n