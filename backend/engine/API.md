# Frozen Engine API Specification (v1.0.0)

This document specifies the frozen public interfaces of the MR-RAG engine. The platform interacts with the engine exclusively through these classes and methods.

## Phase 1: Document Intelligence (Parsing & Indexing Orchestration)

### `ProductionParsingOrchestrator`
Class responsible for orchestrating document parsing, canonical normalization, representation building, and storage registry.
* **Module Path**: `engine.document_pipeline.orchestrator`
* **Initialization**:
  ```python
  orchestrator = ProductionParsingOrchestrator(base_dir: str = None)
  ```
* **Key Methods**:
  * `process_document(filepath: str, force_reparse: bool = False, trace_fn = None) -> str`
    * Computes SHA-256 of the PDF content.
    * Parses PDF using VLM.
    * Normalizes it to Canonical Document representation.
    * Executes all representation builders.
    * Returns `document_id`.
  * `rebuild_representations(document_id: str, targets: List[str] = None, force: bool = False, trace_fn = None) -> str`
    * Performs dependency invalidation and triggers incremental rebuild of specific builders (e.g. chunks, graphs, layouts, embeddings).

---

## Phase 2: Hybrid Retrieval (Expert Ensemble & Fusion)

### `RetrievalOrchestrator`
Ensemble retrieval driver coordinating experts, evidence collection, and context optimization.
* **Module Path**: `engine.document_retrieval.orchestrator`
* **Initialization**:
  ```python
  retriever = RetrievalOrchestrator(store: DocumentStore = None)
  ```
* **Key Methods**:
  * `retrieve(query: str, doc_id: str, top_k: int = 5, token_limit: int = 4000, session_id: str = None) -> Dict[str, Any]`
    * Parses the query and executes experts (Vector, Graph, Entity, Table, Layout) in parallel.
    * Performs evidence expansion, candidate building, fusion, reranking, and context optimization.
    * Manages conversation-aware session memory.
    * Returns dictionary containing:
      * `"query"`: Raw query
      * `"query_understanding"`: QueryAnalyzer output
      * `"final_context"`: List of candidate chunks
      * `"confidence_distribution"`: Calibrated retrieval confidence
      * `"latencies"`: Latency breakdown per expert and step

---

## Phase 3: Answer Generation

### `AnswerOrchestrator`
Coordinates the plan-generate-verify-reflect lifecycle to construct accurate, citation-backed answers.
* **Module Path**: `engine.answer_generation.orchestrator`
* **Initialization**:
  ```python
  generator = AnswerOrchestrator()
  ```
* **Key Methods**:
  * `generate_answer(query: str, qu: QueryUnderstanding, candidates: List[Candidate], retrieval_confidence: float = 0.8, max_retries: int = 1) -> AnswerResult`
    * Executes validation, planning, prompt formatting, model invocation, and claim verification.
    * Returns `AnswerResult` containing:
      * `text`: Post-processed citation-backed answer.
      * `citations`: List of citations linked to candidates.
      * `verification`: Verification output (validity, contradictions, unsupported claims).
      * `confidence`: Computed confidence score.
      * `metrics`: Token usage, LLM cost, generation & verification latencies.
