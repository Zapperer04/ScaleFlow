"""
Smoke test for document_preprocessor -- full image analysis path with Poppler.
Sets PREPROCESS_POPPLER_PATH before any imports so the module-level probe picks it up.
"""
import sys, os

POPPLER_BIN = r"C:\Users\Kaustav\AppData\Local\Microsoft\WinGet\Packages\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe\poppler-25.07.0\Library\bin"

# Must be set BEFORE importing document_preprocessor so _probe_pdf2image() uses it
os.environ["PREPROCESS_POPPLER_PATH"] = POPPLER_BIN
# Fix Windows terminal encoding
sys.stdout.reconfigure(encoding="utf-8")

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
    r = evaluate_document(path)
    print(f"[{label}]")
    print(f"  pages={r.page_count}  encrypted={r.is_encrypted}  corrupted={r.is_corrupted}")
    print(f"  quality={r.overall_quality:.1f}  needs_enhancement={r.needs_enhancement}")
    print(f"  blur={r.blur_score:.1f}  contrast={r.contrast_score:.1f}  noise={r.noise_score:.1f}  skew={r.skew_angle:.2f}deg")
    print(f"  dpi={r.dpi_estimate}  text_ratio={r.extractable_text_ratio:.2%}")
    print(f"  hw={r.has_handwriting}(score={r.handwriting_score:.2f})  sig={r.has_signature}  tbl={r.has_table}  img_region={r.has_image_region}")
    print(f"  is_heavily_handwritten={r.is_heavily_handwritten}  sampled=[{','.join(str(p+1) for p in r.sampled_pages)}]")
    print(f"  eval_ms={r.evaluation_duration_ms:.0f}ms")
    if r.warnings:
        for w in r.warnings:
            print(f"  WARN: {w}")

    # Assertions
    if "malformed" in label:
        assert r.page_count == 0 or r.is_corrupted, f"Expected malformed to exit early: {r}"
    elif "clean typed" in label:
        assert not r.needs_enhancement or r.dpi_estimate is None, f"Clean typed PDF should not need enhancement unless DPI unknown: {r.overall_quality}"
    elif "mixed content" in label:
        # Mixed/partial content must NEVER be hard-rejected (is_heavily_handwritten is just a flag)
        assert not r.is_encrypted and not r.is_corrupted, "Mixed doc must not be hard-rejected"
    print()

print("=== SMOKE TEST COMPLETE ===")
