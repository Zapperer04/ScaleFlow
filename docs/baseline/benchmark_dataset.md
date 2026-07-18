# Benchmark Dataset Specification

To evaluate ingestion performance changes in subsequent stages, the following standardized dataset must be used:

| Category | File | Description | Target Evaluation Metric |
| :--- | :--- | :--- | :--- |
| **Digital PDF** | `digital_report.pdf` | standard text report with clean index tables | Extraction completeness |
| **Scanned PDF** | `scanned_invoice.pdf` | multi-page poor-contrast invoice scan | OCR/VLM fallback success |
| **Handwritten** | `handwritten_form.pdf` | user fill-in form with cursive writing | Preprocessor warning trigger |
| **Multilingual** | `global_doc.pdf` | standard document with Chinese and English | Translation/Encoding rate |\n