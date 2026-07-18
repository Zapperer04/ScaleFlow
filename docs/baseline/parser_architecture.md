# Parser Architecture

ScaleFlow uses a multi-tier fallback parsing layout to process digital and scanned documents.

```mermaid
graph TD
    A[Start Parse] --> B{Is Digital & has text?}
    B -->|Yes| C[PyPDF / PDFPlumber]
    B -->|No| D[VLM layout parser / OCR]
    C --> E[Extract Text & Structural Nodes]
    D --> F[VLM Extraction API call]
    E --> G[Document Graph Builder]
    F --> G
```

## Parser Fallback & Hierarchy
1. **PyPDF / PDFPlumber**: Primary tier for digital documents with indexable character maps. High performance, zero API costs.
2. **OCR / VLM (OpenRouter / Gemini)**: Secondary tier for scanned documents or complex structures (tables, invoices). Reconstructs layout into a hierarchical graph using visual-language models.\n