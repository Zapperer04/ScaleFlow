# Architecture Overview (MR-RAG v1.0)

This document outlines the high-level system architecture, subsystems, data flow, and pipeline stages of the ScaleFlow MR-RAG platform.

## High-Level System Architecture

The system splits cleanly into three primary conceptual layers:
1. **MR-RAG Ingestion & Extraction Engine**: The frozen core processing documents into canonical formats, extracting layout graphs, vectorizing representations, and updating vector databases.
2. **Serving & Platform Layer**: Provides Flask API gateways, authentication handlers, rate limiters, Redis task brokers, and task execution worker nodes.
3. **Evaluation & Benchmarking Framework**: Out-of-process suite validating retrieval quality, system latencies, and scalability gates.

```mermaid
graph TD
    UI[Frontend User Interface] -->|Upload / Chat| Gateway[Flask API Gateway]
    
    subgraph Serving Platform
        Gateway -->|Enqueue Ingestion| Broker[(Redis Queue)]
        Gateway -->|Verify Tokens / RBAC| Auth[Auth & Permissions Manager]
        Broker -.->|Dequeue| Worker1[Worker Node 1]
        Broker -.->|Dequeue| Worker2[Worker Node 2]
    end
    
    subgraph Core Ingestion & Retrieval Engine
        Worker1 -->|1. Ingest PDF| Parser[VLM-First Parser]
        Parser -->|2. Normalize Layout| Normalizer[Canonical Normalizer]
        Normalizer -->|3. Build Reps| Builders[Representation Builders]
        Builders -->|Vector Index| VectorStore[(Qdrant DB)]
        Builders -->|Graph Index| GraphStore[(SQLite Graph DB)]
        
        Gateway -->|Search Query| Retriever[Retrieval Orchestrator]
        Retriever -->|Intent Mapping| Experts[Expert Ensemble]
        Experts -->|Query Vectors| VectorStore
        Experts -->|Hop Expansion| GraphStore
    end
```

---

## Indexing & Processing Pipeline

The indexing pipeline takes a raw PDF document and constructs its multi-representation layout:

```mermaid
sequenceDiagram
    participant Worker
    participant Parser as VLM-First Parser
    participant Norm as Normalizer
    participant Builders as Builders (Chunk, Embed, Graph)
    participant DB as Qdrant & SQLite
    
    Worker->>Parser: Ingest PDF file
    Parser->>Parser: Read Pages (Fallback OCR if scanned)
    Parser-->>Norm: Raw extracted tokens & boxes
    Norm->>Norm: Build Canonical Document JSON
    Norm-->>Builders: Normalized blocks & entities
    Builders->>Builders: Generate text chunking
    Builders->>Builders: Generate sentence embeddings
    Builders->>Builders: Build layout node hierarchies
    Builders-->>DB: Upsert vectors, entities, and graph edges
    DB-->>Worker: Return indexing pipeline completed
```

---

## Retrieval Pipeline

The retrieval orchestrator routes queries dynamically to parallel experts:

```mermaid
graph LR
    Query[User Query] --> Intent[Query Intent Detector]
    Intent --> Routing[Expert Router]
    
    subgraph Expert Ensemble
        Routing -->|Factual / Semantic| Vector[Vector Expert]
        Routing -->|Structural Hops| Graph[Graph Expert]
        Routing -->|Organizations / Persons| Entity[Entity Expert]
        Routing -->|Rows / Columns| Table[Table Expert]
        Routing -->|Document Pages| Layout[Layout Expert]
    end
    
    Vector & Graph & Entity & Table & Layout --> Fusion[Reciprocal Rank Fusion]
    Fusion --> Reranker[Cross-Encoder Reranker]
    Reranker --> Optimizer[Context Optimizer]
    Optimizer --> Final[Optimized Context Chunks]
```

This ensures that the system is **Production Qualified under the evaluated benchmark suite**.
