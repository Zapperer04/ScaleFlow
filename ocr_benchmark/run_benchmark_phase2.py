"""
Master runner — executes all 6 benchmark phases sequentially.
Each phase runs in its own subprocess call so that engine-level crashes are isolated.
Run from repo root:
    .\\ocr_benchmark\\venv_ocr_benchmark\\Scripts\\python .\\ocr_benchmark\\run_benchmark_phase2.py
"""

import subprocess, sys, os
from pathlib import Path

VENV_PY  = Path(__file__).parent / "venv_ocr_benchmark" / "Scripts" / "python.exe"
if not VENV_PY.exists():
    # Fallback for non-Windows
    VENV_PY = Path(__file__).parent / "venv_ocr_benchmark" / "bin" / "python"

BENCHMARK_DIR = Path(__file__).parent

PHASES = [
    ("Phase 1 — Rendering",         BENCHMARK_DIR / "run_phase1_rendering.py"),
    ("Phase 2 — Extraction",        BENCHMARK_DIR / "run_phase2_extraction.py"),
    ("Phase 3 — Latency / Memory",  BENCHMARK_DIR / "run_phase3_latency.py"),
    ("Phase 4 — Retrieval",         BENCHMARK_DIR / "run_phase4_retrieval.py"),
    ("Phase 5 — WER/CER/Table",     BENCHMARK_DIR / "run_phase5_quality.py"),
    ("Phase 6 — Recommendation",    BENCHMARK_DIR / "generate_final_recommendation.py"),
]


def run_phase(name: str, script: Path) -> bool:
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")
    result = subprocess.run(
        [str(VENV_PY), str(script)],
        cwd=str(BENCHMARK_DIR.parent),  # repo root
    )
    if result.returncode != 0:
        print(f"\n  ❌ {name} FAILED (exit code {result.returncode})")
        return False
    print(f"\n  ✅ {name} COMPLETE")
    return True


def main():
    print("ScaleFlow OCR Benchmark — Phase 2")
    print("Isolated environment:", str(VENV_PY))

    for name, script in PHASES:
        ok = run_phase(name, script)
        if not ok and "Phase 2" in name:
            print("\n  FATAL: Extraction failed. Cannot continue to Phase 3+")
            sys.exit(1)

    print("\n" + "=" * 60)
    print("  ALL PHASES COMPLETE")
    print("=" * 60)
    print(f"\nDeliverable reports:")
    for report in [
        "rendering_validation_report.md",
        "ocr_extraction_validation.md",
        "warm_vs_cold_benchmark.md",
        "retrieval_quality_validation.md",
        "recovery_rate_report.md",
        "final_ocr_architecture_recommendation.md",
    ]:
        p = BENCHMARK_DIR / report
        status = "✅" if p.exists() else "❌ MISSING"
        print(f"  {status}  {report}")


if __name__ == "__main__":
    main()
