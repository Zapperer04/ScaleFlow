# Architecture v1.1: Golden Dataset Infrastructure Design

This document details the design and deployment of the Golden Dataset framework, which forms the regression testing baseline for future ScaleFlow upgrades.

## Objective
To lock down current parser behavior, document graphs, text chunk boundaries, metadata formatting, and retrieval outputs. The framework ensures that refactoring steps do not introduce unintended semantic drift.

## Component Specifications

### 1. Generation Script (`tests/utilities/generate_golden_dataset.py`)
- Walks all categories in `tests/fixtures/`.
- Issues API requests to upload and run files.
- Retrieves and normalizes artifacts (`parser_output.json`, `document_graph.json`, `chunks.json`, `metadata.json`).
- Issues query pipelines for standard queries and captures results (`retrieval_queries.json`, `retrieval_results.json`).

### 2. Hash Generation (`tests/utilities/hash_outputs.py`)
- Standardizes output formatting by sorting dictionary keys and rounding floats.
- Creates unique SHA256 signatures for each artifact.
- Updates `tests/golden/manifest.json`.

### 3. Contract Verification (`tests/utilities/validate_dataset.py`)
- Verifies integrity constraints, duplicates, empty elements, and schema validity.

### 4. Regression Comparisons (`tests/utilities/compare_outputs.py`)
- Run checks to ensure that modifications to parsing, chunking, or retrieval modules are flag-notified.
