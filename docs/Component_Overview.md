# Component Overview (MR-RAG v1.0)

This document provides a detailed breakdown of the internal components comprising the frozen core MR-RAG engine.

---

## 1. Document Intelligence Parser

The parsing layer is responsible for converting raw PDFs into structured markdown/JSON content:
- **VLMParser**: The primary parser. Uses Vision-Language Models to transcribe document pages, identifying reading orders, headers, tables, images, and entities.
- **Layout Fallback Parser**: Activates if VLM is unavailable. Uses `pdfplumber` to extract precision layout lines, tables, and bounding boxes.
- **PyPDF Fallback Parser**: Activates as a secondary tier for clean digital PDFs to quickly extract stream text.
- **Tesseract OCR Fallback**: Activates on scanned or noisy documents when text density falls below limits.

---

## 2. Multi-Representation Indexer

Once parsed, the indexer maps the document into different logical representations:
- **Semantic Chunker**: Splits document text into chunks keeping contextual/sentence boundaries.
- **Graph Builder**: Indexes parent-child hierarchies (e.g., sections, headers, paragraphs) into a SQLite structural graph DB.
- **Table Builder**: Converts layout tables into normalized cell coordinates and references.
- **Entity Builder**: Extracts key persons, dates, and organizations.
- **Vector Embedding Builder**: Converts chunk text into dense vectors and upserts them to Qdrant.

---

## 3. Dynamic Router & Ensemble Retriever

Retrieval coordinates search strategies using query analysis:
- **Query Analyzer**: Evaluates query type (factual, tabular, entity, summary) and maps it to target collection targets.
- **Experts**:
  - `VectorExpert`: Queries Qdrant dense vector index.
  - `GraphExpert`: Queries SQLite graph database for neighbor hops.
  - `EntityExpert`: Queries entity indexes.
  - `TableExpert`: Queries table grids.
  - `LayoutExpert`: Queries bounding boxes and page flow order.
- **Fusion Engine**: Merges expert lists using Reciprocal Rank Fusion (RRF).
- **Reranker**: Re-evaluates merged candidates using a MS-MARCO Cross-Encoder.

---

## 4. Verified Answer Generator

The final layer synthesizes the output response:
- **Context Optimizer**: Formats retrieved chunks to fit within LLM token constraints.
- **Answer Planner**: Builds a step-by-step logic plan before model generation.
- **Response Generator**: Asks the LLM to complete the answer.
- **Answer Verifier**: Validates generated statements against the retrieved source chunks, rejecting any unsupported assertions (self-reflection).

These components ensure the engine remains **Production Qualified under the evaluated benchmark suite**.
