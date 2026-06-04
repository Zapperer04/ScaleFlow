import os
import sys
import time
import json
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

POPPLER_BIN = r"C:\Users\Kaustav\AppData\Local\Microsoft\WinGet\Packages\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe\poppler-25.07.0\Library\bin"
os.environ["PREPROCESS_POPPLER_PATH"] = POPPLER_BIN

from services.document_preprocessor import evaluate_document
from services.pdf_parser import parse_pdf
import config

TEST_DATA_DIR = REPO_ROOT / "backend" / "test_data"

TEST_DOCS = {
    "A": ("category_A_simple.pdf", "DIGITAL", False, False, False),
    "B": ("category_B_low_dpi.pdf", "DIGITAL", False, False, False),
    "C": ("category_C_skewed.pdf", "DIGITAL", False, False, False),
    "D": ("category_D_noisy.pdf", "SCANNED", False, False, False),
    "E": ("photographed_notes.pdf", "SCANNED", False, False, False),
    "F": ("category_F_large_doc.pdf", "MIXED", True, False, False),
    "G": ("category_G_handwritten_names.pdf", "SCANNED", False, False, True),
    "H": ("category_H_handwritten.pdf", "SCANNED", False, False, True),
}

def audit_routing():
    print("\n--- Auditing Area 1: Routing Validation ---")
    results = {}
    
    correct = 0
    total = 0
    fps = 0
    fns = 0
    
    for cat, (fname, expected_type, exp_tbl, exp_sig, exp_hw) in TEST_DOCS.items():
        fpath = TEST_DATA_DIR / fname
        if not fpath.exists():
            print(f"File {fname} not found!")
            continue
            
        print(f"Evaluating {fname}...")
        report = evaluate_document(str(fpath))
        
        predicted = report.document_type
        conf = report.routing_confidence
        
        results[cat] = {
            "name": fname,
            "expected_type": expected_type,
            "predicted_type": predicted,
            "confidence": conf,
            "extractable_ratio": report.extractable_text_ratio,
            "image_area_ratio": report.image_area_ratio,
            "page_text_density": report.page_text_density,
            "ocr_text_ratio": report.ocr_text_ratio
        }
        
        total += 1
        if expected_type == predicted:
            correct += 1
        else:
            if expected_type == "DIGITAL" and predicted in ["SCANNED", "MIXED"]:
                fps += 1
            elif expected_type in ["SCANNED", "MIXED"] and predicted == "DIGITAL":
                fns += 1
                
        print(f"  Expected: {expected_type} | Actual: {predicted} (Conf: {conf:.2f})")
        
    acc = correct / total if total > 0 else 0
    print(f"\nReal Routing Accuracy: {acc:.1%} ({correct}/{total})")
    print(f"Real False Positives (DIGITAL -> SCANNED/MIXED): {fps}")
    print(f"Real False Negatives (SCANNED/MIXED -> DIGITAL): {fns}")
    
    return results

def main():
    print("=== STARTING EVIDENCE AUDIT ===")
    results_routing = audit_routing()
    
    # Store results to artifacts
    art_dir = Path(r"C:\Users\Kaustav\.gemini\antigravity-ide\brain\07e03dee-9a3c-44ae-8e91-51b22b0f52ae")
    art_dir.mkdir(parents=True, exist_ok=True)
    
    with open(art_dir / "scratch" / "audit_routing_results.json", "w") as f:
        json.dump(results_routing, f, indent=2)

if __name__ == "__main__":
    main()
