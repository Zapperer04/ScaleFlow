# ScaleFlow Demo Guide

This guide provides a polished, 5-minute narrative for demonstrating the ScaleFlow Orchestration Runtime during engineering interviews. It highlights system stability, deterministic orchestration, and resilient PDF processing.

## ⏱️ The 5-Minute Narrative Flow

### 1. The Setup (0:00 - 1:00)
- **Action:** Open `http://localhost:3000`. Show the clean, operational UI.
- **Talking Point:** "This is ScaleFlow, a distributed document orchestration runtime. The architecture leverages Flask, Redis queues, and multiple independent worker nodes. The primary design goal was strict deterministic execution and high resilience against bad data."
- **Action:** Point out the Live Trace Stream on the right side.
- **Talking Point:** "We built a real-time observability layer. You'll see worker assignments and telemetry pipe directly into this console, allowing us to trust the execution state without checking server logs."

### 2. The Happy Path (1:00 - 2:30)
- **Action:** Upload a standard text PDF (e.g., `test_data/category_A_simple.pdf`).
- **Talking Point:** "Let's ingest a standard document. Notice how the task is queued, and the trace stream immediately picks up the assignment."
- **Action:** Watch the Pipeline Execution Stages table populate.
- **Talking Point:** "The orchestrator splits the workload into four isolated steps: Parse, Chunk, Embed, and Index. By keeping these decoupled in Redis, if a worker crashes during embedding, we don't lose the parsed document."

### 3. The Fallback Resilience Demo (2:30 - 3:30)
- **Action:** Upload a malformed or scanned PDF (e.g., `test_data/category_D_scanned.pdf`).
- **Talking Point:** "Now let's test system resilience. Standard LLM pipelines break when they hit scanned PDFs. Here, we implemented a 3-tier fallback architecture."
- **Action:** Highlight the trace stream logs indicating a fallback.
- **Talking Point:** "As you can see in the trace stream, `PyPDF` failed to extract text, so the worker automatically failed over to `PDFPlumber`, and finally escalated to `Tesseract OCR`. We guarantee extraction without silently dropping the file, and we expose this recovery explicitly to the operator."

### 4. Resource Governance (3:30 - 4:00)
- **Action:** Discuss the hard limits without necessarily executing an exploit.
- **Talking Point:** "To prevent chunk explosion and OOM (Out Of Memory) crashes, the system enforces hard limits: `MAX_CHUNKS` (500) and `MEMORY_LIMIT_MB` (1.5GB). Exceeding these raises explicit exceptions, preventing cascading failure across the distributed workers."

### 5. Retrieval & Validation (4:00 - 5:00)
- **Action:** Open the Retrieval/Chat interface on the platform. Ask a factual question about the uploaded document.
- **Talking Point:** "Finally, because our orchestration is deterministic, our embeddings are perfectly aligned. The system uses Qdrant to retrieve the semantic chunks and generates grounded answers."
- **Action:** Mention the automated tests.
- **Talking Point:** "We certify this stability using an automated integration suite that validates TXT determinism, PDF fallback chains, and retrieval accuracy. The platform is functionally complete."

---

## 💡 Anticipated Interview Questions & Answers

**Q: Why use Redis and RQ instead of something like Celery or Kafka?**
*A: RQ provides exactly what we needed: simple, lightweight, Python-native job queues backed by Redis, without the operational overhead of Kafka or the heavy configuration footprint of Celery. It allowed us to focus on the pipeline logic rather than broker management.*

**Q: What happens if a worker dies mid-task?**
*A: The task remains in the Redis queue and is moved to a failed registry or can be configured to auto-retry. Because our stages (Parse, Chunk, Embed) are granular, we only retry the specific stage that failed, not the entire document pipeline.*

**Q: How do you handle chunking?**
*A: We use a semantic chunking approach that respects paragraph boundaries rather than blindly splitting by character count. This ensures context isn't sheared in half before sending it to the HuggingFace `all-MiniLM-L6-v2` embedding model.*

**Q: Why didn't you use LangChain/LangGraph for orchestration?**
*A: We explicitly avoided heavy abstractions to maintain full control over the runtime, error boundaries, and observability. By building the orchestration layer directly over Redis, the pipeline is fully transparent and significantly easier to debug.*
