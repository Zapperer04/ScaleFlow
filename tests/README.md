# Golden Dataset Regression Baseline Framework

This framework establishes a strict regression baseline to protect ScaleFlow parser, retrieval, and document graph contracts from regression or deviation during future refactoring phases.

## Directory Structure

```
tests/
├── README.md
├── fixtures/               # Input documents to process
│   ├── digital/            # Native digital PDFs/files
│   ├── scanned/            # Scanned PDFs (OCR fallback path)
│   ├── mixed/              # Mixed layout files
│   ├── tables/             # Tabular layouts
│   ├── forms/              # Structured form templates
│   ├── multicolumn/        # Multi-column documents
│   └── images/             # Visual-only documents
│
├── expected/               # Ground-truth golden outputs
│   └── <document_name>/
│       ├── parser_output.json
│       ├── document_graph.json
│       ├── chunks.json
│       ├── metadata.json
│       ├── retrieval_queries.json
│       └── retrieval_results.json
│
├── golden/
│   └── manifest.json       # SHA256 hashes of expected files
│
└── utilities/
    ├── generate_golden_dataset.py
    ├── compare_outputs.py
    ├── validate_dataset.py
    └── hash_outputs.py
```

## How to Run & Verify

All utilities support the standard production CLI arguments:
- `--fixtures`: Fixture path (default: `tests/fixtures`)
- `--output`: Output/expected directory path (default: `tests/expected`)
- `--only`: Commas-separated patterns of doc names to run
- `--skip`: Commas-separated patterns of doc names to skip
- `--force`: Force overwrite existing baseline files/manifest
- `--workers`: Number of parallel workers/threads
- `--verbose`: Enable detailed log output

### 1. Generating Outputs

Run the generation utility to run fixtures against the current running pipeline:
```bash
python tests/utilities/generate_golden_dataset.py --verbose
```

### 2. Updating Hashes

Calculate the SHA256 hashes of the generated outputs and update `manifest.json`:
```bash
python tests/utilities/hash_outputs.py
```

### 3. Validating the Dataset

Verify syntax, schemas, empty outputs, duplicates, and architectural contracts:
```bash
python tests/utilities/validate_dataset.py
```

### 4. Running Regression Checks (Comparison)

Compare new outputs against the golden hashes and generate a `comparison_report.md`:
```bash
python tests/utilities/compare_outputs.py
```
