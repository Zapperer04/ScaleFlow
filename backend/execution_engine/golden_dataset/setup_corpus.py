import os
import shutil
import yaml

TEST_DATA_DIR = "backend/test_data"
GOLDEN_DIR = "backend/execution_engine/golden_dataset"

CATEGORIES = {
    "forms": {
        "file": "category_A_simple.pdf",
        "meta": {
            "category": "forms",
            "characteristics": ["form-like", "simple layout", "key-value pairs"]
        }
    },
    "tables": {
        "file": "synthetic_table.pdf",
        "meta": {
            "category": "tables",
            "characteristics": ["dense tables", "structured grid", "numerical data"]
        }
    },
    "invoices": {
        "file": "category_C_skewed.pdf",
        "meta": {
            "category": "invoices",
            "characteristics": ["invoice layout", "skewed text", "tabular lines"]
        }
    },
    "receipts": {
        "file": "category_D_scanned.pdf",
        "meta": {
            "category": "receipts",
            "characteristics": ["receipt layout", "dense vertical listing", "faded ink"]
        }
    },
    "contracts": {
        "file": "category_C_large.pdf",
        "meta": {
            "category": "contracts",
            "characteristics": ["legal language", "dense paragraphs", "signatures block"]
        }
    },
    "research_papers": {
        "file": "category_B_academic.pdf",
        "meta": {
            "category": "research_papers",
            "characteristics": ["academic format", "two-column layout", "equations", "citations"]
        }
    },
    "books": {
        "file": "billion_dollar_sure_thing.pdf",
        "meta": {
            "category": "books",
            "characteristics": ["standard book format", "sequential headers", "continuous text"]
        }
    },
    "multicolumn": {
        "file": "category_F_large_doc.pdf",
        "meta": {
            "category": "multicolumn",
            "characteristics": ["multi-column layout", "embedded images", "sidebars"]
        }
    },
    "scanned": {
        "file": "category_D_noisy.pdf",
        "meta": {
            "category": "scanned",
            "characteristics": ["scanned PDF", "high noise", "background artifacts", "low contrast"]
        }
    },
    "handwritten": {
        "file": "category_H_handwritten.pdf",
        "meta": {
            "category": "handwritten",
            "characteristics": ["handwritten notes", "variable cursive stroke", "non-standard alignments"]
        }
    },
    "diagrams": {
        "file": "photographed_notes.pdf",
        "meta": {
            "category": "diagrams",
            "characteristics": ["photographed diagram", "flowcharts", "hand-drawn lines"]
        }
    },
    "mixed": {
        "file": "category_B_low_dpi.pdf",
        "meta": {
            "category": "mixed",
            "characteristics": ["low DPI scan", "mixed text and graphics", "varying orientations"]
        }
    }
}

def setup():
    print("Setting up Golden Document Corpus...")
    os.makedirs(GOLDEN_DIR, exist_ok=True)
    for cat_name, info in CATEGORIES.items():
        cat_path = os.path.join(GOLDEN_DIR, cat_name)
        os.makedirs(cat_path, exist_ok=True)
        
        src_file = os.path.join(TEST_DATA_DIR, info["file"])
        dst_file = os.path.join(cat_path, info["file"])
        
        if os.path.exists(src_file):
            shutil.copy2(src_file, dst_file)
            print(f"Copied {info['file']} to {cat_path}/")
        else:
            print(f"Warning: Source file {src_file} does not exist.")
            
        meta_file = os.path.join(cat_path, "metadata.yaml")
        with open(meta_file, "w") as f:
            yaml.safe_dump(info["meta"], f)
            print(f"Created metadata.yaml in {cat_path}/")

if __name__ == "__main__":
    setup()
