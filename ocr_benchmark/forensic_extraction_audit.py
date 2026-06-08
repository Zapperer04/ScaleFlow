import sys, os, json
from pathlib import Path
import pypdf

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

DOCS = {
    "Cat E": "backend/test_data/preprocessed_verify_E.pdf",
    "Cat G": "backend/test_data/category_G_handwritten_names.pdf",
}

def run_audit():
    print("# Forensic Extraction Audit (Categories E & G)\n")
    
    for cat, rel_path in DOCS.items():
        print(f"## {cat} ({os.path.basename(rel_path)})")
        filepath = str(REPO_ROOT / rel_path)
        
        if not os.path.exists(filepath):
            print(f"**Error**: File not found at {filepath}\n")
            continue
            
        try:
            reader = pypdf.PdfReader(filepath)
            page_count = len(reader.pages)
            print(f"- Total Pages: {page_count}")
            
            for i, page in enumerate(reader.pages):
                txt = page.extract_text() or ""
                char_count = len(txt.strip())
                
                print(f"\n### Page {i+1}")
                print(f"- **Extractable Char Count**: {char_count}")
                
                if char_count > 0:
                    preview = txt.strip().replace("\n", "\\n")
                    if len(preview) > 100:
                        preview = preview[:100] + "..."
                    print(f"- **Preview**: `{preview}`")
                else:
                    print("- **Preview**: (empty)")
                    
                # Inspect resources (fonts, images) to see why text extraction might fail
                resources = page.get("/Resources", {})
                fonts = resources.get("/Font", {})
                xobjects = resources.get("/XObject", {})
                
                font_count = len(fonts)
                image_count = sum(1 for k, v in xobjects.items() if v.get("/Subtype") == "/Image")
                
                print(f"- **Fonts**: {font_count} | **Images**: {image_count}")
                
        except Exception as e:
            print(f"**Error parsing {cat}**: {e}")
        print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    run_audit()
