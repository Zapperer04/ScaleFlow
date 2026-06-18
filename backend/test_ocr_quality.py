import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from services.pdf_parser import _extract_page_ocr, OCR_AVAILABLE
from services.quality_gate_service import compute_quality_score
import pypdf

print("OCR Available:", OCR_AVAILABLE)
filepath = "test_data/Kaustav_OOPsAssign2.pdf"

# 1. Primary parse (pypdf)
reader = pypdf.PdfReader(filepath)
pypdf_text_parts = []
for i in range(len(reader.pages)):
    pypdf_text_parts.append(reader.pages[i].extract_text() or "")
pypdf_text = "\n\n".join(pypdf_text_parts)
print("\n--- Measuring Primary (PyPDF) Extract Quality ---")
pypdf_score, pypdf_signals = compute_quality_score(pypdf_text, "SCANNED")
print(f"PyPDF Output Length: {len(pypdf_text)} chars")
print(f"PyPDF Quality Metrics: {pypdf_signals} (Score: {pypdf_score})")

# 2. OCR parse (page 1 to 3 to keep it fast)
ocr_text_parts = []
for i in range(min(5, len(reader.pages))):
    print(f"Running OCR on page {i+1}...")
    page_text, page_conf = _extract_page_ocr(filepath, i)
    ocr_text_parts.append(page_text)
ocr_text = "\n\n".join(ocr_text_parts)
print("\n--- Measuring OCR Quality ---")
ocr_score, ocr_signals = compute_quality_score(ocr_text, "SCANNED")
print(f"OCR Output Length: {len(ocr_text)} chars")
print(f"OCR Quality Metrics: {ocr_signals} (Score: {ocr_score})")
