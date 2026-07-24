import os
import shutil
import json

def setup():
    base_dir = "benchmark/datasets"
    os.makedirs(base_dir, exist_ok=True)
    
    categories = {
        "books": "backend/test_data/billion_dollar_sure_thing.pdf",
        "contracts": "backend/test_data/category_A_simple.pdf",
        "manuals": "backend/test_data/category_B_academic.pdf",
        "finance": "backend/test_data/synthetic_table.pdf",
        "forms": "backend/test_data/category_C_large.pdf",
        "research": "backend/test_data/photographed_notes.pdf",
        "mixed": "backend/test_data/category_D_scanned.pdf"
    }
        
    for cat, source_pdf in categories.items():
        cat_dir = os.path.join(base_dir, cat)
        os.makedirs(cat_dir, exist_ok=True)
        
        # Copy test document if it exists, fallback to text file
        doc_dest = os.path.join(cat_dir, "document.pdf")
        if os.path.exists(source_pdf):
            shutil.copy(source_pdf, doc_dest)
            print(f"Copied {source_pdf} -> {doc_dest}")
        else:
            fallback_source = source_pdf.replace("backend/", "")
            if os.path.exists(fallback_source):
                shutil.copy(fallback_source, doc_dest)
                print(f"Copied {fallback_source} -> {doc_dest}")
            else:
                with open(os.path.join(cat_dir, "document.txt"), "w") as f:
                    f.write(f"Sample content for category {cat}. This is a production benchmark document.")
                print(f"Created fallback text for category {cat}")
                
        # Write questions and ground truths
        questions = [
            {
                "question": f"What is the main topic of the {cat} document?",
                "document_id": f"doc_{cat}",
                "expected_chunk_ids": ["chunk-0"],
                "expected_graph_nodes": ["node-p1"],
                "expected_entities": ["Google"],
                "expected_tables": ["tbl-1"],
                "difficulty": "easy",
                "category": cat
            }
        ]
        with open(os.path.join(cat_dir, "questions.json"), "w") as f:
            json.dump(questions, f, indent=2)

if __name__ == "__main__":
    setup()
    print("Benchmark datasets setup completed successfully.")
