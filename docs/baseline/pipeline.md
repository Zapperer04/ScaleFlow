# Ingestion Pipeline

ScaleFlow runs a linear/directed acyclic graph ingestion pipeline.

```mermaid
graph LR
    Upload[Upload PDF] --> Preprocess[Preprocessing]
    Preprocess --> Parse[VLM/OCR Parsing]
    Parse --> Graph[Graph Creation]
    Graph --> Chunk[Semantic Chunking]
    Chunk --> Embed[Embedding Generation]
    Embed --> BM25[BM25 Indexing]
```

## Stage Overview

1. **Document Upload**: Raw files are POSTed to `/files/upload` and saved in `storage/uploads/`.
2. **Preprocessing (`preprocess_document`)**: Uses image processing (Poppler, OpenCV-like logic in `document_preprocessor.py`) to detect blur, low contrast, low text characters, page limits, and handwriting score. Generates a preprocessing report.
3. **Parsing (`parse_document`)**: Employs a fallback strategy: PyPDF -> PDFPlumber -> OCR/VLM extraction. VLM mode utilizes external LLM models (e.g. Gemini 2.5 Flash, Gemma-4) to extract structured nodes.
4. **Document Graph**: Persists hierarchical relationships (headings, sections, paragraphs, tables) in SQLite/PostgreSQL as a Graph.
5. **Chunking (`chunk_text`)**: Breaks text into semantic paragraphs and tables based on graph relationships, respecting word boundaries and maximum tokens/character configs.
6. **Embeddings (`generate_embeddings`)**: Generates vectors using HuggingFace sentence-transformers (`BAAI/bge-base-en-v1.5`) and registers them in Qdrant.
7. **BM25 Indexing (`build_bm25_index`)**: Builds sparse index collections on local filesystem for multi-stage search.\n