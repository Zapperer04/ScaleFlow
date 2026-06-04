"""
Phase 1 — Rendering Verification
Loads Poppler path from backend/.env, renders page 1 of each benchmark PDF,
validates image dimensions, and writes rendering_validation_report.md.
"""

import os, sys, time
from pathlib import Path

# ── Locate repo root & load .env ─────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

def _load_env():
    env_path = REPO_ROOT / "backend" / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
_load_env()

POPPLER_PATH = os.getenv("PREPROCESS_POPPLER_PATH", "").strip() or None
TEST_DATA_DIR = REPO_ROOT / "backend" / "test_data"
RENDERED_DIR  = Path(__file__).parent / "rendered"
RENDERED_DIR.mkdir(exist_ok=True)

CATEGORIES = {
    "B": TEST_DATA_DIR / "category_B_low_dpi.pdf",
    "C": TEST_DATA_DIR / "category_C_skewed.pdf",
    "D": TEST_DATA_DIR / "category_D_noisy.pdf",
    "E": TEST_DATA_DIR / "photographed_notes.pdf",
    "F": TEST_DATA_DIR / "category_F_large_doc.pdf",
    "G": TEST_DATA_DIR / "category_G_handwritten_names.pdf",
    "H": TEST_DATA_DIR / "category_H_handwritten.pdf",
}


def render_category(cat: str, pdf_path: Path) -> dict:
    result = {
        "cat": cat,
        "pdf_path": str(pdf_path),
        "exists": pdf_path.exists(),
        "page_count": None,
        "render_success": False,
        "render_duration_s": None,
        "image_path": None,
        "width_px": None,
        "height_px": None,
        "failure_reason": None,
    }

    if not result["exists"]:
        result["failure_reason"] = "PDF file does not exist"
        return result

    try:
        import pypdf
        reader = pypdf.PdfReader(str(pdf_path), strict=False)
        result["page_count"] = len(reader.pages)
    except Exception as e:
        result["failure_reason"] = f"pypdf open failed: {e}"
        return result

    try:
        from pdf2image import convert_from_path
        t0 = time.perf_counter()
        imgs = convert_from_path(
            str(pdf_path),
            dpi=300,
            first_page=1,
            last_page=1,
            poppler_path=POPPLER_PATH,
        )
        dur = time.perf_counter() - t0

        if not imgs:
            result["failure_reason"] = "convert_from_path returned empty list"
            return result

        img = imgs[0]
        out_path = RENDERED_DIR / f"cat_{cat}.png"
        img.save(str(out_path))

        result["render_success"] = True
        result["render_duration_s"] = round(dur, 3)
        result["image_path"] = str(out_path)
        result["width_px"] = img.width
        result["height_px"] = img.height
    except Exception as e:
        result["failure_reason"] = str(e)

    return result


def generate_report(results: list) -> str:
    lines = [
        "# Phase 1 — Rendering Validation Report",
        "",
        f"Poppler path: `{POPPLER_PATH or 'system PATH'}`",
        "",
        "| Category | PDF Exists | Pages | Render | Duration (s) | Width × Height | Failure Reason |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    for r in results:
        exists  = "✅" if r["exists"] else "❌"
        render  = "✅" if r["render_success"] else "❌"
        pages   = str(r["page_count"]) if r["page_count"] is not None else "N/A"
        dur     = str(r["render_duration_s"]) if r["render_duration_s"] else "N/A"
        dims    = f"{r['width_px']} × {r['height_px']}" if r["width_px"] else "N/A"
        fail    = r["failure_reason"] or ""
        lines.append(f"| {r['cat']} | {exists} | {pages} | {render} | {dur} | {dims} | {fail} |")

    successes = sum(1 for r in results if r["render_success"])
    lines += [
        "",
        f"**Rendered successfully:** {successes}/{len(results)}",
        "",
        "## Rendered Image Paths",
        "",
    ]
    for r in results:
        if r["render_success"]:
            lines.append(f"- Cat **{r['cat']}**: `{r['image_path']}`")

    return "\n".join(lines)


def main():
    print("=== Phase 1: Rendering Verification ===")
    results = []
    for cat, path in CATEGORIES.items():
        print(f"  Rendering Category {cat}: {path.name}")
        r = render_category(cat, path)
        results.append(r)
        status_ascii = "OK" if r["render_success"] else f"FAIL: {r['failure_reason']}"
        print(f"    -> {status_ascii}")

    report = generate_report(results)
    out = Path(__file__).parent / "rendering_validation_report.md"
    out.write_text(report, encoding="utf-8")
    print(f"\nReport written: {out}")
    return results


if __name__ == "__main__":
    main()
