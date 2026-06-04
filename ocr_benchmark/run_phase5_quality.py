"""
Phase 5 — Quality Metrics: Recovery Rate, WER/CER, Table Recovery
Loads extracted texts, computes:
  - Recovery Rate: keyword recall per category
  - WER/CER: vs ground truth extracted from PDF text layer (pypdf)
  - Table Recovery: fraction of expected table cells found in extracted text (Cat F)
Writes recovery_rate_report.md.
"""

import os, sys
from pathlib import Path

REPO_ROOT     = Path(__file__).resolve().parent.parent
EXTRACTED_DIR = Path(__file__).parent / "extracted"
TEST_DATA_DIR = REPO_ROOT / "backend" / "test_data"

CATEGORIES = ["B", "C", "D", "E", "F", "G", "H"]
ENGINES    = ["Tesseract", "PaddleOCR", "EasyOCR", "DocTR", "Surya"]

PDF_PATHS = {
    "B": TEST_DATA_DIR / "category_B_low_dpi.pdf",
    "C": TEST_DATA_DIR / "category_C_skewed.pdf",
    "D": TEST_DATA_DIR / "category_D_noisy.pdf",
    "E": TEST_DATA_DIR / "photographed_notes.pdf",
    "F": TEST_DATA_DIR / "category_F_large_doc.pdf",
    "G": TEST_DATA_DIR / "category_G_handwritten_names.pdf",
    "H": TEST_DATA_DIR / "category_H_handwritten.pdf",
}

EXPECTED_KEYWORDS = {
    "B": ["throughput", "ledger", "distributed"],
    "C": ["replication", "nodes", "reliability"],
    "D": ["document", "test"],
    "E": ["photographed", "lighting"],
    "F": ["authorization", "table"],
    "G": ["john", "handwriting"],
    "H": ["handwritten", "cursive"],
}

# Table cells expected in Category F (mixed content doc)
TABLE_CELLS_F = ["name", "date", "amount", "total", "authorization", "description"]


def get_ground_truth(cat: str) -> str:
    """Extract digital text layer from PDF via pypdf as ground-truth reference."""
    pdf_path = PDF_PATHS.get(cat)
    if not pdf_path or not pdf_path.exists():
        return ""
    try:
        import pypdf
        reader = pypdf.PdfReader(str(pdf_path), strict=False)
        pages = []
        for page in reader.pages:
            try:
                pages.append(page.extract_text() or "")
            except Exception:
                pass
        return "\n".join(pages)
    except Exception:
        return ""


def compute_wer_cer(hypothesis: str, reference: str):
    """
    Compute WER and CER using jiwer.
    Returns (wer, cer) tuple. Returns (None, None) if jiwer unavailable or reference empty.
    """
    if not reference.strip() or not hypothesis.strip():
        return None, None
    try:
        import jiwer
        # Normalize
        ref_clean = " ".join(reference.lower().split())
        hyp_clean = " ".join(hypothesis.lower().split())
        if not ref_clean:
            return None, None
        wer = round(jiwer.wer(ref_clean, hyp_clean), 4)
        cer = round(jiwer.cer(ref_clean, hyp_clean), 4)
        return wer, cer
    except Exception:
        return None, None


def compute_table_recovery(text: str, cells: list) -> float:
    """Fraction of expected table cells found in extracted text (case-insensitive)."""
    if not text.strip():
        return 0.0
    hits = sum(1 for cell in cells if cell.lower() in text.lower())
    return round(hits / len(cells), 3) if cells else 0.0


def analyze_engine(engine: str, ground_truths: dict) -> dict:
    results = {}
    for cat in CATEGORIES:
        p = EXTRACTED_DIR / f"{engine}_{cat}.txt"
        text = p.read_text(encoding="utf-8") if p.exists() else ""

        expected = EXPECTED_KEYWORDS.get(cat, [])
        hits = [kw for kw in expected if kw.lower() in text.lower()]
        recovery = round(len(hits) / len(expected), 3) if expected else 0.0

        gt = ground_truths.get(cat, "")
        wer, cer = compute_wer_cer(text, gt)

        table_rec = None
        if cat == "F":
            table_rec = compute_table_recovery(text, TABLE_CELLS_F)

        results[cat] = {
            "char_count":      len(text),
            "recovery_rate":   recovery,
            "keyword_hits":    hits,
            "wer":             wer,
            "cer":             cer,
            "table_recovery":  table_rec,
            "ground_truth_chars": len(gt),
        }
    return results


def generate_report(all_results: dict) -> str:
    lines = [
        "# Phase 5 — Recovery Rate, WER/CER, and Table Recovery Report",
        "",
        "## Recovery Rate by Engine and Category",
        "",
        "| Engine | Cat | Chars | Recovery | Keyword Hits |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]
    for eng, cats in all_results.items():
        for cat, r in cats.items():
            hits = ", ".join(r["keyword_hits"]) or "none"
            lines.append(f"| {eng} | {cat} | {r['char_count']} | {r['recovery_rate']:.1%} | {hits} |")

    lines += [
        "",
        "## WER / CER by Engine and Category",
        "",
        "> WER = Word Error Rate (substitution+deletion+insertion / reference words)",
        "> CER = Character Error Rate (same formula at character level)",
        "> Lower is better. N/A = ground truth empty or extraction empty.",
        "",
        "| Engine | Cat | WER | CER | GT chars | Extracted chars |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    for eng, cats in all_results.items():
        for cat, r in cats.items():
            wer  = f"{r['wer']:.4f}" if r["wer"] is not None else "N/A"
            cer  = f"{r['cer']:.4f}" if r["cer"] is not None else "N/A"
            gt   = r["ground_truth_chars"]
            ext  = r["char_count"]
            lines.append(f"| {eng} | {cat} | {wer} | {cer} | {gt} | {ext} |")

    lines += [
        "",
        "## Table Recovery (Category F Only)",
        "",
        f"Expected table cells: `{', '.join(TABLE_CELLS_F)}`",
        "",
        "| Engine | Table Cell Recovery | Score |",
        "| :--- | :--- | :--- |",
    ]
    for eng, cats in all_results.items():
        r = cats.get("F", {})
        tr = r.get("table_recovery")
        score = f"{tr:.1%}" if tr is not None else "N/A"
        bar = ("█" * int((tr or 0) * 10)).ljust(10) if tr is not None else " " * 10
        lines.append(f"| {eng} | {bar} | {score} |")

    return "\n".join(lines)


def main():
    print("=== Phase 5: Recovery Rate, WER/CER, Table Recovery ===")

    # Pre-load ground truths (once)
    ground_truths = {}
    for cat in CATEGORIES:
        gt = get_ground_truth(cat)
        ground_truths[cat] = gt
        print(f"  Ground truth Cat {cat}: {len(gt)} chars")

    all_results = {}
    for eng in ENGINES:
        print(f"\n  Analyzing {eng}...")
        r = analyze_engine(eng, ground_truths)
        all_results[eng] = r
        for cat, m in r.items():
            wer = f"{m['wer']:.4f}" if m["wer"] is not None else "N/A"
            print(f"    Cat {cat}: {m['char_count']} chars | recovery={m['recovery_rate']:.1%} | WER={wer}")

    report = generate_report(all_results)
    out = Path(__file__).parent / "recovery_rate_report.md"
    out.write_text(report, encoding="utf-8")
    print(f"\nReport written: {out}")
    return all_results


if __name__ == "__main__":
    main()
