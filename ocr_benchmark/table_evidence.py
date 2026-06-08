import sys, os, json, time
from pathlib import Path
import pdfplumber

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

CAT_F_PATH = REPO_ROOT / "backend" / "test_data" / "category_F_large_doc.pdf"

def extract_tables_as_markdown(filepath):
    """Extracts tables from a PDF using pdfplumber and returns markdown."""
    markdown_tables = []
    
    with pdfplumber.open(filepath) as pdf:
        for i, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            for t_idx, table in enumerate(tables):
                # Convert table to markdown
                lines = []
                for row_idx, row in enumerate(table):
                    cleaned_row = [str(cell).replace("\n", " ").strip() if cell else "" for cell in row]
                    lines.append("| " + " | ".join(cleaned_row) + " |")
                    
                    if row_idx == 0:
                        lines.append("|" + "|".join(["---"] * len(cleaned_row)) + "|")
                
                md_table = "\n".join(lines)
                markdown_tables.append({"page": i+1, "table_idx": t_idx+1, "markdown": md_table})
                
    return markdown_tables

if __name__ == "__main__":
    print("=== Table Extraction Evidence (Category F) ===")
    t0 = time.time()
    tables = extract_tables_as_markdown(str(CAT_F_PATH))
    print(f"Extraction took {time.time()-t0:.2f}s")
    print(f"Found {len(tables)} tables.")
    
    if tables:
        print("\n--- Example Markdown Conversion ---")
        print(tables[0]["markdown"])
        
    out_path = REPO_ROOT / "ocr_benchmark" / "cat_f_tables.json"
    out_path.write_text(json.dumps(tables, indent=2), encoding="utf-8")
    print(f"\nSaved raw tables to {out_path}")
