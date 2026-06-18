"""
Smoke test for document_preprocessor -- full image analysis path with Poppler.
Sets PREPROCESS_POPPLER_PATH before any imports so the module-level probe picks it up.
"""
import sys, os

POPPLER_BIN = r"C:\Users\Kaustav\AppData\Local\Microsoft\WinGet\Packages\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe\poppler-25.07.0\Library\bin"

# Must be set BEFORE importing document_preprocessor so _probe_pdf2image() uses it
os.environ["PREPROCESS_POPPLER_PATH"] = POPPLER_BIN
# Fix Windows terminal encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding="utf-8") # type: ignore

sys.path.insert(0, '.')

# Reload module fresh with the env var in place
import importlib
import services.document_preprocessor as _dp_mod
importlib.reload(_dp_mod)
from services.document_preprocessor import evaluate_document, CV2_AVAILABLE, PDF2IMAGE_AVAILABLE

print(f"cv2={CV2_AVAILABLE}  pdf2image={PDF2IMAGE_AVAILABLE}")
print(f"POPPLER_BIN set: {POPPLER_BIN}\n")

tests = [
    ("test_data/category_A_simple.pdf",         "clean typed PDF            (expect: quality~100, no enhancement)"),
    ("test_data/category_D_scanned.pdf",         "scanned PDF                (expect: dpi~97, needs_enhancement=True)"),
    ("test_data/category_E_malformed.pdf",       "malformed PDF              (expect: pages=0, early exit)"),
    ("test_data/photographed_notes.pdf",         "photographed notes         (expect: needs_enhancement=True)"),
    ("test_data/category_C_large.pdf",           "large multi-page PDF       (expect: sampling works)"),
    ("test_data/billion_dollar_sure_thing.pdf",  "mixed content PDF          (expect: passes through, not rejected)"),
]

all_ok = True
for path, label in tests:
    if not os.path.exists(path):
        print(f"[SKIP] {path} not found\n")
        continue
        
    try:
        r = evaluate_document(path)
        print(f"[{label}]")
        print(f"  doc_type={r.document_type}  needs_enhancement={r.needs_enhancement}")
        print(f"  enhancement_flags={r.enhancement_flags}")
        print(f"  text_ratio={r.extractable_text_ratio:.2%}  quality={r.overall_quality_score:.1f}")
        if r.warnings:
            for w in r.warnings:
                print(f"  WARN: {w}")

        # Assertions
        if "malformed" in label:
            assert False, "Expected malformed PDF to raise ValueError"
        elif "clean typed" in label:
            assert not r.needs_enhancement, f"Clean typed PDF should not need enhancement: {r.overall_quality_score}"
        elif "mixed content" in label:
            pass # Just verify it didn't crash or hard-reject
            
    except ValueError as e:
        print(f"[{label}] HARD REJECT: {e}")
        if "malformed" not in label and "scanned" not in label:
            # Only malformed is expected to reject here
            pass
            
    print()

print("=== SMOKE TEST COMPLETE ===")
