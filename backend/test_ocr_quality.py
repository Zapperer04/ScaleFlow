import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from services.pdf_parser import _extract_page_ocr, evaluate_text_quality, OCR_AVAILABLE
import pypdf

print("OCR Available:", OCR_AVAILABLE)
filepath = "test_data/Kaustav_OOPsAssign2.pdf"

# 1. Primary parse (pypdf)
reader = pypdf.PdfReader(filepath)
pypdf_text_parts = []
for i in range(len(reader.pages)):
    pypdf_text_parts.append(reader.pages[i].extract_text() or "")
pypdf_text = "\n\n".join(pypdf_text_parts)
pypdf_metrics = evaluate_text_quality(pypdf_text)
print("PYPDF METRICS:", pypdf_metrics)

# 2. OCR parse (page 1 to 3 to keep it fast)
ocr_text_parts = []
for i in range(min(5, len(reader.pages))):
    print(f"Running OCR on page {i+1}...")
    page_text, page_conf = _extract_page_ocr(filepath, i)
    ocr_text_parts.append(page_text)
ocr_text = "\n\n".join(ocr_text_parts)
ocr_metrics = evaluate_text_quality(ocr_text)
print("OCR METRICS:", ocr_metrics)
