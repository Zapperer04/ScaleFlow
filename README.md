# ScaleFlow: Distributed AI Document Orchestration Runtime

ScaleFlow is a distributed, fault-tolerant document orchestration runtime built for scalable ingestion, complex PDF recovery, and high-precision RAG (Retrieval-Augmented Generation). 

This project demonstrates deterministic worker orchestration, resilient parser fallbacks (including OCR), semantic chunking, and verifiable vector indexing, controlled via a unified UI with real-time execution telemetry.

## 🏗️ Architecture

```mermaid
graph TD
    UI[Frontend UI] --> |Upload / Chat| API[Flask API Gateway]
    
    API --> |Enqueue Task| Redis[(Redis Task Queue)]
    API --> |Store File| Storage[(Local Storage / NFS)]
    
    subgraph Distributed Workers [Distributed Worker Nodes]
        W1[Worker 1]
        W2[Worker 2]
        W3[Worker 3]
    end
    
    Redis -.-> |Dequeue Task| Distributed Workers
    
    subgraph Orchestration [Task Orchestration Pipeline]
        Distributed Workers --> |1. Parse Document| Parser[PDF Pipeline]
        Distributed Workers --> |2. Semantic Chunk| Chunker[Text Chunker]
        Distributed Workers --> |3. Embed| Embedder[Sentence-Transformers]
        Distributed Workers --> |4. Index| VectorStore[(Qdrant Vector DB)]
    end
    
    Parser --> |Failover 1: PyPDF| P1[PyPDF2]
    P1 -.-> |Fallback| P2[PDFPlumber]
    P2 -.-> |Fallback| P3[Tesseract OCR]
```

## 🚀 Core Features

1. **Deterministic Execution Orchestration:** Uses distributed Redis queues to process large document workflows deterministically. Tasks do not get lost.
2. **Resilient PDF Fallback Architecture:** 
   - Tier 1: Fast parsing via `PyPDF`.
   - Tier 2: Precision layout parsing via `pdfplumber`.
   - Tier 3: Visual parsing via `Tesseract OCR` (for scanned or malformed PDFs).
3. **Resource Governance:** Built-in safeguards protect against memory blowouts and chunk explosions (strictly limits to 500 chunks and 1.5GB memory per process, raising explicit `RuntimeError` rather than silently degrading).
4. **Live Execution Telemetry:** Operational UI featuring sticky-scroll terminal-style event streaming, color-coded severities, and worker tagging.
5. **Retrieval-Augmented Generation (RAG):** Full integration with Qdrant for vectorized context retrieval against HuggingFace embeddings (`all-MiniLM-L6-v2`).

## 🛠️ Tech Stack

- **Backend:** Python, Flask, RQ (Redis Queue), SentenceTransformers
- **Vector Store:** Qdrant
- **Data Store & Locks:** Redis
- **Frontend:** React, Vanilla CSS (Engineering-focused Design System)
- **Deployment:** Docker Compose

## 🏃‍♂️ Docker Setup & Running Locally

1. **Prerequisites:** Ensure Docker and Docker Compose are installed.
2. **Start the Platform:**
   ```bash
   docker compose up -d --build
   ```
   *This single command builds the UI, the API, the Redis cluster, the Qdrant DB, and 3 independent worker nodes.*
3. **Access the UI:** 
   Navigate to `http://localhost:3000`
4. **Access the Backend API:**
   Navigate to `http://localhost:5000`

## 🧪 Validation & Stability 

The project includes a comprehensive, automated stability test suite (`run_all_validations.py`):
1. **TXT Determinism Validation:** Asserts that identical workloads processed across randomized workers produce byte-identical vector layouts 20/20 times.
2. **PDF Fallback Validation:** Tests 5 categories of PDFs (Simple, Multi-column, Large, Scanned, Malformed) to prove failover recovery (e.g., verifying OCR activates appropriately on scanned documents).
3. **Retrieval Quality Validation:** Tests Factual, Semantic, and Contextual queries against indexed test documents to guarantee RAG precision.

## 🛑 Known Limits

- The current OCR pipeline relies on CPU execution, which may be slow for >100-page scanned documents.
- Redis is run in standalone mode (no clustered failover for the queue itself).
- Vector indexing operates in local memory mode for Qdrant unless configured otherwise in production environments.

## 🔮 Future Improvements

- Add GPU support for the embedding/OCR worker nodes.
- Implement LangGraph for multi-agent reasoning over retrieved context.
- Introduce advanced caching layers for duplicate document ingestion.
