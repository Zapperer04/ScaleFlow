import sys, os, json
from pathlib import Path
import cv2

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from services.document_preprocessor import _analyze_pages, _probe_text

# The actual files and their GROUND TRUTH ideal routes
DOCS = {
    "Cat A": ("backend/test_data/category_A_simple.pdf", "DIGITAL"),
    "Cat B": ("backend/test_data/category_B_low_dpi.pdf", "SCANNED"),
    "Cat C": ("backend/test_data/category_C_skewed.pdf", "SCANNED"),
    "Cat D": ("backend/test_data/category_D_noisy.pdf", "SCANNED"),
    "Cat E": ("backend/test_data/preprocessed_verify_E.pdf", "MIXED"),
    "Cat F": ("backend/test_data/category_F_large_doc.pdf", "DIGITAL"), 
    "Cat G": ("backend/test_data/category_G_handwritten_names.pdf", "MIXED"),
    "Cat H": ("backend/test_data/category_H_handwritten.pdf", "SCANNED"),
}

# In Cat F (large doc), if it's 100% digital, it should be DIGITAL.
# If it has some images, MIXED. Let's see what the signals say.

def run_simulation():
    print("# Routing Simulation Evidence\n")
    
    current_correct = 0
    proposed_correct = 0
    total = len(DOCS)
    
    results = []
    
    for cat, (rel_path, gt_route) in DOCS.items():
        filepath = str(REPO_ROOT / rel_path)
        if not os.path.exists(filepath):
            continue
            
        text_info = _probe_text(filepath, [0,1,2,3,4][:5])
        extractable_text_ratio = text_info["extractable_text_ratio"]
        
        # Hack to run _analyze_pages directly
        import pypdf
        reader = pypdf.PdfReader(filepath)
        page_count = len(reader.pages)
        sampled = list(range(min(5, page_count)))
        
        img_signals = _analyze_pages(filepath, sampled)
        
        # --- Current Logic ---
        page_types_current = img_signals["page_types"]
        num_pages = len(page_types_current)
        if num_pages == 0:
            continue
            
        num_digital = page_types_current.count("digital")
        num_scanned = page_types_current.count("scanned")
        digital_ratio_curr = num_digital / num_pages
        scanned_ratio_curr = num_scanned / num_pages
        
        if digital_ratio_curr >= 0.90:
            curr_route = "DIGITAL"
        elif scanned_ratio_curr >= 0.90:
            curr_route = "SCANNED"
        else:
            curr_route = "MIXED"
            
        # --- Proposed Logic ---
        # 1. Relax page level classification: >= 50 digital chars -> digital
        page_types_prop = []
        for i in sampled:
            # Re-implement page level logic inside the script
            try:
                txt = reader.pages[i].extract_text() or ""
                digital_char_count = len(txt.strip())
            except:
                digital_char_count = 0
                
            # PROPOSED PAGE RULE: Just rely on digital text presence.
            # If a page has 50 chars of extractable text, it's digital!
            if digital_char_count >= 50:
                page_types_prop.append("digital")
            else:
                page_types_prop.append("scanned")
                
        num_digital_prop = page_types_prop.count("digital")
        digital_ratio_prop = num_digital_prop / num_pages
        
        # PROPOSED DOC RULE: 100% digital -> DIGITAL, 100% scanned -> SCANNED, else MIXED
        if digital_ratio_prop == 1.0:
            prop_route = "DIGITAL"
        elif digital_ratio_prop == 0.0:
            prop_route = "SCANNED"
        else:
            prop_route = "MIXED"
            
        # Stats
        if curr_route == gt_route: current_correct += 1
        if prop_route == gt_route: proposed_correct += 1
        
        results.append({
            "cat": cat,
            "gt": gt_route,
            "curr_route": curr_route,
            "prop_route": prop_route,
            "img_area": img_signals["image_area_ratio"],
            "ocr_ratio": img_signals["ocr_text_ratio"],
            "curr_page_types": page_types_current,
            "prop_page_types": page_types_prop
        })
        
    print("## Confusion Matrix & Accuracy")
    print(f"- Current Accuracy: {current_correct}/{total} ({(current_correct/total)*100:.1f}%)")
    print(f"- Proposed Accuracy: {proposed_correct}/{total} ({(proposed_correct/total)*100:.1f}%)\n")
    
    print("## Raw Signals & Routing Decisions")
    print("| Category | GT | Current | Proposed | Img Area | Curr Pages | Prop Pages |")
    print("|---|---|---|---|---|---|---|")
    for r in results:
        c_mark = "PASS" if r["curr_route"] == r["gt"] else "FAIL"
        p_mark = "PASS" if r["prop_route"] == r["gt"] else "FAIL"
        print(f"| {r['cat']} | {r['gt']} | {r['curr_route']} {c_mark} | {r['prop_route']} {p_mark} | {r['img_area']:.2f} | {r['curr_page_types']} | {r['prop_page_types']} |")

if __name__ == "__main__":
    run_simulation()
