import sys, os, json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from services.document_preprocessor import evaluate_document

DOCS = {
    "Cat B": "category_B_low_dpi.pdf",
    "Cat C": "category_C_skewed.pdf",
    "Cat F": "category_F_large_doc.pdf"
}

CORPUS_DIR = REPO_ROOT / "ocr_benchmark" / "corpus"

for name, filename in DOCS.items():
    print(f"=== {name} ({filename}) ===")
    path = str(CORPUS_DIR / filename)
    report = evaluate_document(path)
    
    # document_type is assigned inside evaluate_document but not saved in PreprocessingReport?
    # Wait, document_type is returned in evaluate_document?
    print(report)
    print("--------------------------------------------------\n")
