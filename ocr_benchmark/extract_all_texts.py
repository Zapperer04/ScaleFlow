"""
extract_all_texts.py - Extract and save all corpus texts for ground truth reconstruction.
"""
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import os
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))
os.environ["PREPROCESS_POPPLER_PATH"] = r"C:\Users\Kaustav\AppData\Local\Microsoft\WinGet\Packages\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe\poppler-25.07.0\Library\bin"

import logging
logging.basicConfig(level=logging.WARNING)

from services.pdf_parser import parse_pdf

TEST_DATA_DIR = REPO_ROOT / "backend" / "test_data"
SCRATCH_DIR = Path(r"C:\Users\Kaustav\.gemini\antigravity-ide\brain\07e03dee-9a3c-44ae-8e91-51b22b0f52ae\scratch")
SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

DOCS = {
    "A": "category_A_simple.pdf",
    "B": "category_B_low_dpi.pdf",
    "C": "category_C_skewed.pdf",
    "D": "category_D_noisy.pdf",
    "E": "photographed_notes.pdf",
    "F": "category_F_large_doc.pdf",
    "G": "category_G_handwritten_names.pdf",
    "H": "category_H_handwritten.pdf",
}

out = {}
for cat, fname in DOCS.items():
    fpath = TEST_DATA_DIR / fname
    print(f"Parsing Cat {cat}: {fname} ...")
    res = parse_pdf(str(fpath), document_type="MIXED", routing_confidence=1.0)
    out[cat] = {
        "fname": fname,
        "chars": len(res.text),
        "text": res.text,
    }
    # Print first 300 chars so we can see the content
    preview = res.text[:300].replace("\n", " | ")
    print(f"  -> {len(res.text)} chars | preview: {preview}")

out_path = SCRATCH_DIR / "all_corpus_texts.json"
out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"\nSaved to {out_path}")
