# Document Intelligence Hardening — Validation Report
**Date:** 2026-05-29 18:25:12

## Summary
| Category | File | Parse Status | Parser Used | Duration | Chunks |
|---|---|---|---|---|---|
| A | category_A_simple.pdf | completed | pypdf | 134.65s | 1 |
| B | category_B_academic.pdf | completed | pypdf | 10.88s | 1 |
| C | category_C_large.pdf | completed | pypdf | 39.96s | 200 |
| D | category_D_scanned.pdf | completed | ocr_fallback | 8.78s | 0 |
| E | category_E_malformed.pdf | failed | N/A | 30.76s | 0 |
| P | photographed_notes.pdf | completed | ocr_fallback | 6.34s | 0 |
| S | billion_dollar_sure_thing.pdf | completed | ocr_fallback | 12.7s | 1 |
| K | Kaustav_OOPsAssign2.pdf | failed | pypdf | 123.77s | 0 |

### Category A: Simple Text PDF
- **Status**: SUCCESS
- **Parser Used**: pypdf
- **OCR Activated**: NO
- **OCR Attempted**: NO
- **OCR Confidence**: 100.0%
- **Printable Ratio**: 100.00%
- **Dictionary Word Ratio**: 52.94%
- **Coherence Score**: 90.2/100.0
- **Initial Parser Quality Score**: 67.8/100.0
- **OCR Parser Quality Score**: 0.0/100.0
- **First 500 Extracted Characters**: `ScaleFlow Category A Test Document This is a simple text PDF designed to test basic parsing capabilities. It has no images, no complex layout, and should be parsed instantly by pypdf without falling back to pdfplumber or OCR. The sky is blue and the grass is green. This is a factual statement for retrieval.`
- **Chunks Generated**: 1
- **Duration**: 134.65s

**Retrieval Tests:**
- *Q: What color is the sky?*
  - *A: Based on the retrieved context, here are the most relevant sections matching your query:

Source [1] (Confidence Score: 0.2115): "ScaleFlow Category A Test Document This is a simple text PDF designed to test basic parsing capabilities. It has no images, no complex layout, and should be parsed instantly by pypdf without falling back to pdfplumber or OCR. The sky is blue and the grass is green. This is a factual statement for retrieval."*
- *Q: What is this document designed to test?*
  - *A: Based on the retrieved context, here are the most relevant sections matching your query:

Auto-generated Document Summary (Confidence Score: 0.95):
SUMMARY:
ScaleFlow Category A Test Document This is a simple text PDF designed to test basic parsing capabilities. It has no images, no complex layout, and should be parsed instantly by pypdf without falling back to pdfplumber or OCR. The sky is blue and the grass is green. This is a factual statement for retrieval.

Source [2] (Confidence Score: 0.4403): "ScaleFlow Category A Test Document This is a simple text PDF designed to test basic parsing capabilities. It has no images, no complex layout, and should be parsed instantly by pypdf without falling back to pdfplumber or OCR. The sky is blue and the grass is green. This is a factual statement for retrieval."*

### Category B: Academic PDF (equations/references)
- **Status**: SUCCESS
- **Parser Used**: pypdf
- **OCR Activated**: NO
- **OCR Attempted**: NO
- **OCR Confidence**: 100.0%
- **Printable Ratio**: 100.00%
- **Dictionary Word Ratio**: 51.16%
- **Coherence Score**: 93.0/100.0
- **Initial Parser Quality Score**: 67.9/100.0
- **OCR Parser Quality Score**: 0.0/100.0
- **First 500 Extracted Characters**: `Advanced Orchestration in Distributed Systems Jane Doe, John Smith Abstract: This paper explores the performance of distributed DAG execution in highly volatile environments. We present ScaleFlow, a novel orchestration engine. E = mc^2 + sum(x_i) / N References: [1] Lamport, L. (1978). Time, clocks, and the ordering of events in a distributed system.`
- **Chunks Generated**: 1
- **Duration**: 10.88s

### Category C: Large PDF (50+ pages)
- **Status**: SUCCESS
- **Parser Used**: pypdf
- **OCR Activated**: NO
- **OCR Attempted**: NO
- **OCR Confidence**: 100.0%
- **Printable Ratio**: 100.00%
- **Dictionary Word Ratio**: 68.25%
- **Coherence Score**: 100.0/100.0
- **Initial Parser Quality Score**: 80.9/100.0
- **OCR Parser Quality Score**: 0.0/100.0
- **First 500 Extracted Characters**: `Page 1 of Large Document This is a repeated paragraph to simulate a large document and test chunking caps, memory limits, and timeouts. ScaleFlow must gracefully handle this volume. This is a repeated paragraph to simulate a large document and test chunking caps, memory limits, and timeouts. ScaleFlow must gracefully handle this volume. This is a repeated paragraph to simulate a large document and test chunking caps, memory limits, and timeouts. ScaleFlow must gracefully handle this volume.  Thi`
- **Chunks Generated**: 200
- **Duration**: 39.96s

### Category D: Scanned/Image PDF
- **Status**: SUCCESS
- **Parser Used**: ocr_fallback
- **OCR Activated**: YES
- **OCR Attempted**: NO
- **OCR Confidence**: 82.5%
- **Printable Ratio**: 100.00%
- **Dictionary Word Ratio**: 44.44%
- **Coherence Score**: 72.2/100.0
- **Initial Parser Quality Score**: 55.6/100.0
- **OCR Parser Quality Score**: 0.0/100.0
- **First 500 Extracted Characters**: `This isan image-based PDF. pypdfand pdfplumber will fail to extract this text Itshould trigger the OCR fallback.`
- **Chunks Generated**: 0
- **Duration**: 8.78s

### Category E: Malformed/Corrupted PDF
- **Status**: FAILED (Expected/intended fallback behavior)
- **Error**: Stream has ended unexpectedly
- **Parser Used**: N/A
- **Duration**: 30.76s

### Category P: Photographed Notes PDF
- **Status**: SUCCESS
- **Parser Used**: ocr_fallback
- **OCR Activated**: YES
- **OCR Attempted**: NO
- **OCR Confidence**: 84.7%
- **Printable Ratio**: 100.00%
- **Dictionary Word Ratio**: 21.28%
- **Coherence Score**: 100.0/100.0
- **Initial Parser Quality Score**: 52.8/100.0
- **OCR Parser Quality Score**: 0.0/100.0
- **First 500 Extracted Characters**: `Lecture Notes Introduction to Distributed Systems  1. Replication and Consistency models guarantee state agreements.  2. Vector clocks are used tocapture causal relationships in messages.  3. Raft uses leader election and consensus to replicate logs safely.  4, Paxos isanother consensusalgorithm but is harder toimplement  5. Byzantine fault tolerance handles arbitrary failures including malicious actors.`
- **Chunks Generated**: 0
- **Duration**: 6.34s

### Category S: The Billion Dollar Sure Thing PDF
- **Status**: SUCCESS
- **Parser Used**: ocr_fallback
- **OCR Activated**: YES
- **OCR Attempted**: NO
- **OCR Confidence**: 90.5%
- **Printable Ratio**: 100.00%
- **Dictionary Word Ratio**: 32.23%
- **Coherence Score**: 97.5/100.0
- **Initial Parser Quality Score**: 58.3/100.0
- **OCR Parser Quality Score**: 0.0/100.0
- **First 500 Extracted Characters**: `THE BILLION DOLLAR SURE THING  ANovel by Paul E Erdman  Chapter 1: The Zurich Exchange  Itwasa billion-dollar sure thing, the most secret scheme in Swiss banking history.  The plan was conceived in the quiet wood-paneled offices of the General Bank of Switzerland. Under the guidance of the brilliant but ruthless Dr. Stanley, a group of international bankers sought toexploit the vulnerabilities of the American dollar. If the Americans found out  the entire global financial order would collapse ov`
- **Chunks Generated**: 1
- **Duration**: 12.7s

### Category K: Kaustav OOPs Assignment 2 PDF
- **Status**: FAILED (Expected/intended fallback behavior)
- **Error**: Document unreadable / OCR quality too low: Dictionary-word ratio 6.40% is below threshold 20.00%
- **Parser Used**: pypdf
- **OCR Activated**: NO
- **OCR Attempted**: YES
- **OCR Confidence**: 100.0%
- **Printable Ratio**: 99.89%
- **Dictionary Word Ratio**: 6.40%
- **Coherence Score**: 86.6/100.0
- **Initial Parser Quality Score**: 0.0/100.0
- **OCR Parser Quality Score**: 0.0/100.0
- **First 500 Extracted Characters**: `Kougtay kuman  Class Antmal void cat0{  23fEI0ITEOU220  clos Monnal extend Anirnel voo coalk (0  3sskm.out-paîntln CThis animaJ ca lo od.")  Ciase bog eende Mommal Void bonk0  Sysem-out-pântin (his mamal coalk"):  -2  Sysken 0ut-pnin tln ( The dog baskg.")  public clasg MulilevdInhutanu  Fage : Date :  d alk: d bank;  puble stahe void man (shing CI aNag) bog);  vofd mint0);  void snoj   Clase Den0 împlum eolb Phin habe, howasle publl vold poin+()  pubiic votd ghow () Syakm 0ut fpriatin (" Pninin`
- **Duration**: 123.77s