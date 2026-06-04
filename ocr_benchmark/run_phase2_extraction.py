"""
Phase 2 — OCR Extraction Verification
Runs every OCR engine against each rendered image from Phase 1.
Also runs an image-only synthetic test (plain Pillow PNG) to isolate engine
baseline capability from any PDF/rendering ambiguity.
Writes per-engine extracted texts to extracted/{engine}_{cat}.txt
Generates ocr_extraction_validation.md.
"""

import os, sys, time, traceback
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

RENDERED_DIR  = Path(__file__).parent / "rendered"
EXTRACTED_DIR = Path(__file__).parent / "extracted"
EXTRACTED_DIR.mkdir(exist_ok=True)

CATEGORIES = ["B", "C", "D", "E", "F", "G", "H"]

EXPECTED_KEYWORDS = {
    "B": ["throughput", "ledger", "distributed"],
    "C": ["replication", "nodes", "reliability"],
    "D": ["document", "test"],
    "E": ["photographed", "lighting"],
    "F": ["authorization", "table"],
    "G": ["john", "handwriting"],
    "H": ["handwritten", "cursive"],
}

# Synthetic image text — simple sentence every engine should read
SYNTHETIC_TEXT = "The quick brown fox jumps over the lazy dog."


def make_synthetic_image() -> str:
    """Create a minimal plain-white PNG with printed text for baseline test."""
    img = Image.new("RGB", (600, 100), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((20, 30), SYNTHETIC_TEXT, fill=(0, 0, 0))
    path = str(Path(__file__).parent / "synthetic_test.png")
    img.save(path)
    return path


def load_engine(engine_name: str):
    sys.path.insert(0, str(Path(__file__).parent))
    from benchmark_wrappers import (
        TesseractWrapper, PaddleWrapper, EasyOCRWrapper, DocTRWrapper, SuryaWrapper
    )
    mapping = {
        "Tesseract": TesseractWrapper,
        "PaddleOCR": PaddleWrapper,
        "EasyOCR":   EasyOCRWrapper,
        "DocTR":     DocTRWrapper,
        "Surya":     SuryaWrapper,
    }
    t0 = time.perf_counter()
    wrapper = mapping[engine_name]()
    return wrapper, round(time.perf_counter() - t0, 3)


def run_extraction(engine_name: str) -> dict:
    result = {
        "engine": engine_name,
        "init_time_s": None,
        "init_error": None,
        "synthetic_success": False,
        "synthetic_chars": 0,
        "categories": {},
    }

    try:
        wrapper, init_t = load_engine(engine_name)
        result["init_time_s"] = init_t
    except Exception as e:
        result["init_error"] = traceback.format_exc()
        return result

    # ── Synthetic image-only test ─────────────────────────────────────────────
    synthetic_path = make_synthetic_image()
    try:
        out = wrapper.extract_text(synthetic_path)
        text = out["text"].strip()
        result["synthetic_chars"] = len(text)
        result["synthetic_success"] = len(text) > 5
        result["synthetic_snippet"] = text[:80]
    except Exception as e:
        result["synthetic_error"] = traceback.format_exc()

    # ── Per-category extraction ───────────────────────────────────────────────
    for cat in CATEGORIES:
        img_path = RENDERED_DIR / f"cat_{cat}.png"
        cat_result = {
            "image_exists": img_path.exists(),
            "char_count": 0,
            "latency_s": None,
            "error": None,
            "keyword_hits": [],
        }

        if not img_path.exists():
            cat_result["error"] = "Rendered image not found (Phase 1 failed?)"
            result["categories"][cat] = cat_result
            continue

        try:
            out = wrapper.extract_text(str(img_path))
            text = out["text"] or ""
            cat_result["char_count"] = len(text)
            cat_result["latency_s"] = round(out["latency_s"], 3)

            # Persist extracted text
            txt_out = EXTRACTED_DIR / f"{engine_name}_{cat}.txt"
            txt_out.write_text(text, encoding="utf-8")

            # Keyword hits
            expected = EXPECTED_KEYWORDS.get(cat, [])
            cat_result["keyword_hits"] = [kw for kw in expected if kw.lower() in text.lower()]
        except Exception:
            cat_result["error"] = traceback.format_exc()

        result["categories"][cat] = cat_result

    return result


def must_extract_categories() -> list:
    """Categories B, C, E must have char_count > 0 for at least one engine."""
    return ["B", "C", "E"]


def generate_report(engine_results: list) -> str:
    lines = [
        "# Phase 2 — OCR Extraction Validation Report",
        "",
        "## Synthetic Image-Only Test",
        "",
        "| Engine | Init (s) | Synthetic chars | Success | Snippet |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]
    for er in engine_results:
        eng    = er["engine"]
        init   = str(er["init_time_s"]) if er["init_time_s"] is not None else "FAILED"
        chars  = str(er.get("synthetic_chars", 0))
        ok     = "OK" if er.get("synthetic_success") else "FAIL"
        init_err = er.get("init_error") or ""
        snip   = er.get("synthetic_snippet") or init_err[:60]
        lines.append(f"| {eng} | {init} | {chars} | {ok} | {snip[:70]} |")

    lines += [
        "",
        "## Extraction by Category",
        "",
        "| Engine | Cat | Char Count | Latency (s) | Keyword Hits | Status |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    for er in engine_results:
        for cat, cr in er.get("categories", {}).items():
            eng   = er["engine"]
            chars = cr["char_count"]
            lat   = str(cr["latency_s"]) if cr["latency_s"] else "N/A"
            kw    = ", ".join(cr["keyword_hits"]) or "none"
            ok    = "✅" if chars > 0 else ("⚠️ No image" if not cr["image_exists"] else "❌ Zero chars")
            err   = (" — " + cr["error"][:80].replace("\n", " ")) if cr["error"] else ""
            lines.append(f"| {eng} | {cat} | {chars} | {lat} | {kw} | {ok}{err} |")

    # ── Success/failure summary ───────────────────────────────────────────────
    lines += ["", "## Extraction Success Summary", ""]
    for must_cat in must_extract_categories():
        any_success = any(
            er.get("categories", {}).get(must_cat, {}).get("char_count", 0) > 0
            for er in engine_results
        )
        status = "✅ At least one engine extracted text" if any_success else "❌ ALL engines produced 0 chars — BENCHMARK FAILURE"
        lines.append(f"- **Category {must_cat}:** {status}")

    return "\n".join(lines)


def main():
    print("=== Phase 2: OCR Extraction Verification ===")
    engines = ["Tesseract", "PaddleOCR", "EasyOCR", "DocTR", "Surya"]
    all_results = []

    for eng in engines:
        print(f"\n  Loading {eng}...")
        r = run_extraction(eng)
        all_results.append(r)
        if r["init_error"]:
            print(f"    ❌ Init failed: {r['init_error'][:100]}")
        else:
            print(f"    ✅ Init in {r['init_time_s']}s | Synthetic: {'✅' if r['synthetic_success'] else '❌'}")
            for cat, cr in r["categories"].items():
                print(f"      Cat {cat}: {cr['char_count']} chars | hits: {cr['keyword_hits']}")

    report = generate_report(all_results)
    out = Path(__file__).parent / "ocr_extraction_validation.md"
    out.write_text(report, encoding="utf-8")
    print(f"\nReport written: {out}")
    return all_results


if __name__ == "__main__":
    main()
