# Retrieval Quality Evaluation Report
**Date:** 2026-05-29T12:33:05.452514Z
**Pipeline ID:** 268
---
### Query Type: Factual
**Question:** What is the monthly budget for Project TITAN?
**Expected Keywords:** $4,500, budget
**Result Status:** PASSED
**Confidence:** low
**Synthesized Answer:**
> Based on the retrieved context, here are the most relevant sections matching your query:

Source [1] (Confidence Score: 0.578): "3. Failure Modes & Recovery If a worker crashes during chunking, the orchestrator detects the heartbeat timeout after 15 seconds.  The task is then automatically re-queued and a different worker claims it. This guarantees zero orphaned tasks. In the event of a parser failure (e.g., pypdf fails on a corrupted page), the system falls back to pdfplumber, and ultimately to Tesseract OCR.

4. Infrastructure Costs The current monthly budget for Project TITAN is $4,500. This includes $2,000 for GPU compute instances (for embeddings), $1,500 for the Qdrant managed cluster, and $1,000 for standard application servers."

**Top Retrieved Chunk:**
---

### Query Type: Semantic
**Question:** How does the system handle a situation where a worker node crashes unexpectedly?
**Expected Keywords:** heartbeat timeout, re-queued, 15 seconds
**Result Status:** PASSED
**Confidence:** low
**Synthesized Answer:**
> Based on the retrieved context, here are the most relevant sections matching your query:

Source [1] (Confidence Score: 0.4437): "2. Component Architecture The system consists of three main modules: - API Gateway (Port 5000): Handles incoming requests and orchestrates DAG generation. - Redis Message Broker: Acts as the state-locking and queuing mechanism for the distributed workers. - Qdrant Vector Store: Stores the semantic embeddings for the RAG pipeline. It utilizes an HNSW index for fast nearest-neighbor searches.

3. Failure Modes & Recovery If a worker crashes during chunking, the orchestrator detects the heartbeat timeout after 15 seconds.  The task is then automatically re-queued and a different worker claims it. This guarantees zero orphaned tasks. In the event of a parser failure (e.g., pypdf fails on a corrupted page), the system falls back to pdfplumber, and ultimately to Tesseract OCR."

Source [2] (Confidence Score: 0.3763): "3. Failure Modes & Recovery If a worker crashes during chunking, the orchestrator detects the heartbeat timeout after 15 seconds.  The task is then automatically re-queued and a different worker claims it. This guarantees zero orphaned tasks. In the event of a parser failure (e.g., pypdf fails on a corrupted page), the system falls back to pdfplumber, and ultimately to Tesseract OCR.

4. Infrastructure Costs The current monthly budget for Project TITAN is $4,500. This includes $2,000 for GPU compute instances (for embeddings), $1,500 for the Qdrant managed cluster, and $1,000 for standard application servers."

**Top Retrieved Chunk:**
---

### Query Type: Contextual
**Question:** Which vector database is used and what indexing algorithm does it rely on?
**Expected Keywords:** Qdrant, HNSW
**Result Status:** PASSED
**Confidence:** low
**Synthesized Answer:**
> Based on the retrieved context, here are the most relevant sections matching your query:

Source [1] (Confidence Score: 0.3588): "2. Component Architecture The system consists of three main modules: - API Gateway (Port 5000): Handles incoming requests and orchestrates DAG generation. - Redis Message Broker: Acts as the state-locking and queuing mechanism for the distributed workers. - Qdrant Vector Store: Stores the semantic embeddings for the RAG pipeline. It utilizes an HNSW index for fast nearest-neighbor searches."

Source [2] (Confidence Score: 0.3185): "2. Component Architecture The system consists of three main modules: - API Gateway (Port 5000): Handles incoming requests and orchestrates DAG generation. - Redis Message Broker: Acts as the state-locking and queuing mechanism for the distributed workers. - Qdrant Vector Store: Stores the semantic embeddings for the RAG pipeline. It utilizes an HNSW index for fast nearest-neighbor searches.

3. Failure Modes & Recovery If a worker crashes during chunking, the orchestrator detects the heartbeat timeout after 15 seconds.  The task is then automatically re-queued and a different worker claims it. This guarantees zero orphaned tasks. In the event of a parser failure (e.g., pypdf fails on a corrupted page), the system falls back to pdfplumber, and ultimately to Tesseract OCR."

**Top Retrieved Chunk:**
---
