# ADR-001: VLM-First Document Parsing

## Status
Accepted

## Context
Traditional PDF parsing relies on layout heuristics (e.g. bounding box matching, text stripping) which fail on complex PDFs containing multi-column text, nested tables, vector diagrams, and mathematical formulas. This leads to fragmented canonical representations and degraded downstream retrieval accuracy.

## Decision
We utilize a Vision-Language Model (VLM) parser as the primary entry point for document parsing. The VLM acts as a unified visual reader, outputting a high-fidelity raw markdown/JSON representation of both page layout, coordinates, entities, and textual flow.

## Consequences
- **Pros**:
  - Handles complex documents, graphics, and tables natively.
  - Generates a single, coherent canonical parse.
- **Cons**:
  - Higher initial processing cost and latency compared to rules-based text extractors.
  - Requires fallback mechanisms (like PyPDF/pdfplumber) for offline/low-resource environments.
