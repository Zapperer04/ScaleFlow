import os, sys, json, time, math
import cv2
import numpy as np
from pathlib import Path
from jiwer import cer, wer
from PIL import Image
import pytesseract
os.environ["OMP_NUM_THREADS"] = "1"

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))
import config

os.environ["PREPROCESS_POPPLER_PATH"] = getattr(config, "PREPROCESS_POPPLER_PATH", "") or r"C:\Users\Kaustav\AppData\Local\Microsoft\WinGet\Packages\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe\poppler-25.07.0\Library\bin"

from pdf2image import convert_from_path

# Ground Truth references
GT = {
    "A": "ScaleFlow Category A Test Document This is a simple text PDF designed to test basic parsing capabilities. It has no images, no complex layout, and should be parsed instantly by pypdf without falling back to pdfplumber or OCR. The sky is blue and the grass is green. This is a factual statement for retrieval.",
    "B": "ScaleFlow Category B Low DPI Document Distributed ledger systems require high throughput This low resolution text must be upscaled for OCR.",
    "C": "ScaleFlow Category C Skewed Document Test Replication across nodes ensures reliability. This document has a significant rotation skew angle.",
    "E": "Lecture Notes Introduction to Distributed Systems 1. Replication and Consistency models guarantee state agreements. 2. Vector clocks are used tocapture causal relationships in messages. 3. Raft uses leader election and consensus to replicate logs safely. 4, Paxos isanother consensusalgorithm but is harder toimplement 5. Byzantine fault tolerance handles arbitrary failures including malicious actors.",
    "F": "This is a boilerplate document containing structured information intended to be chunked. The parsing logic must execute accurately to report high-resolution timings for document ingestion under high load."
}

def enhance_image(img, upscale=False, deskew=False):
    cv_img = np.array(img.convert('L'))
    
    if upscale:
        cv_img = cv2.resize(cv_img, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        
    if deskew:
        # Deskew using Hough Transform & minAreaRect
        # Binarize
        _, thresh = cv2.threshold(cv_img, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
        coords = np.column_stack(np.where(thresh > 0))
        angle = cv2.minAreaRect(coords)[-1]
        
        # Handle OpenCV version differences in minAreaRect
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
            
        (h, w) = cv_img.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        cv_img = cv2.warpAffine(cv_img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        
    return cv_img

def get_ocr_text(cv_img):
    img = Image.fromarray(cv_img)
    return pytesseract.image_to_string(img, config="--psm 6")

def main():
    print("Running Phase 5 OCR Enhancement Benchmark...", flush=True)
    
    docs_dir = REPO_ROOT / "backend" / "test_data"
    rendered_dir = REPO_ROOT / "ocr_benchmark" / "rendered"
    
    categories = ["A", "B", "C", "E", "F"]
    pdfs = {
        "A": docs_dir / "category_A_simple.pdf",
        "B": docs_dir / "category_B_low_dpi.pdf",
        "C": docs_dir / "category_C_skewed.pdf",
        "E": docs_dir / "category_E_malformed.pdf",
        "F": docs_dir / "category_F_large_doc.pdf",
    }
    
    variants = [
        ("Baseline", False, False),
        ("Upscale", True, False),
        ("Deskew", False, True),
        ("Upscale+Deskew", True, True)
    ]
    
    results = {}
    
    for cat in categories:
        print(f"Processing Category {cat}...")
        results[cat] = {}
        
        img = None
        rendered_png = rendered_dir / f"cat_{cat}.png"
        if rendered_png.exists():
            img = Image.open(str(rendered_png))
        elif pdfs[cat].exists():
            try:
                images = convert_from_path(str(pdfs[cat]), first_page=1, last_page=1, dpi=200, poppler_path=os.environ["PREPROCESS_POPPLER_PATH"])
                img = images[0]
            except Exception as e:
                print(f"Failed to load PDF for {cat}: {e}")
                continue
        else:
            print(f"No image/PDF found for {cat}")
            continue
            
        for v_name, upscale, deskew in variants:
            t0 = time.time()
            enhanced_cv = enhance_image(img, upscale, deskew)
            ocr_text = get_ocr_text(enhanced_cv)
            latency = time.time() - t0
            
            clean_ocr = " ".join(ocr_text.split()).lower()
            clean_gt = " ".join(GT[cat].split()).lower()
            
            c_err = cer(clean_gt, clean_ocr)
            w_err = wer(clean_gt, clean_ocr)
            
            results[cat][v_name] = {
                "text": ocr_text,
                "cer": float(c_err),
                "wer": float(w_err),
                "latency": latency
            }
            print(f"  [{v_name}] CER: {c_err:.1%} | WER: {w_err:.1%}")
            
    out_path = Path(r"C:\Users\Kaustav\.gemini\antigravity-ide\brain\07e03dee-9a3c-44ae-8e91-51b22b0f52ae\scratch\phase5_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
        
    print("Done. Saved phase5_results.json", flush=True)

if __name__ == "__main__":
    main()
