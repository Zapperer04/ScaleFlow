# ScaleFlow Ingestion Parser Performance Profile
**Generated:** 2026-06-02 15:21:58

This report profiles the performance and fallback decisions of the 3-tier parser chain.

## Average Parsing Durations (Seconds)
| Category | Pages | Parser Used | Open | Page Discovery | pypdf | pdfplumber | OCR | Quality Gate | Routing Overhead |
|---|---|---|---|---|---|---|---|---|---|
| A | 1 | pypdf | 0.0012s | 0.0006s | 0.0046s | 0.0000s | 0.0000s | 0.0004s | 0.0000s |
| B | 1 | pypdf | 0.0015s | 0.0008s | 0.0050s | 0.0000s | 0.0000s | 0.0006s | 0.0000s |
| C | 200 | pypdf | 0.0116s | 0.0661s | 3.2935s | 0.0000s | 0.0000s | 0.4757s | 0.0006s |
| D | 1 | pypdf | 0.0024s | 0.0011s | 0.0019s | 0.0208s | 4.1116s | 0.0000s | 0.0000s |
| E | 0 | N/A | 0.0000s | 0.0000s | 0.0000s | 0.0000s | 0.0000s | 0.0000s | 0.0000s |
| F | 220 | pypdf | 0.0098s | 0.0722s | 3.8180s | 0.0000s | 0.0000s | 0.5457s | 0.0007s |

## In-Depth Parser Diagnostics
1. **Is OCR being triggered unnecessarily?**
   - No. For digital text PDFs (Categories A, B, C, F), OCR duration is 0.0s. OCR fallback and rescue passes only triggered when standard text parsing failed the Printable Ratio or Dictionary Word Ratio thresholds (Category D, or photographed/scanned pages).
2. **Are multiple parsers processing the same document?**
   - Yes, for scanned PDFs (Category D), standard `pypdf` is run first. When it yields less than 20 characters (or low quality), the quality check rejects the primary parse, triggering the OCR rescue pass on all pages.
3. **Is page-level extraction causing excessive latency?**
   - No. Page-level extraction is essential for the incremental checkpoint recovery mechanism and memory capping.
4. **Is parser fallback logic contributing significant overhead?**
   - The routing/priorities check takes < 0.001s, which is completely negligible.