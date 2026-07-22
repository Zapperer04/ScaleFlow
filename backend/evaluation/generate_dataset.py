import json
import os

def generate_questions():
    categories = [
        "Books",
        "Research Papers",
        "Contracts",
        "Invoices",
        "Forms",
        "Technical Manuals",
        "Mixed Documents"
    ]

    questions = []
    
    # Let's generate 50 questions per category -> 350 questions total
    for cat in categories:
        for idx in range(1, 51):
            difficulty = "easy" if idx <= 15 else ("medium" if idx <= 40 else "hard")
            
            # Formulate queries dynamically based on categories
            if cat == "Books":
                query = f"Retrieve key theme and narrative summary in Chapter {idx}"
            elif cat == "Research Papers":
                query = f"What is the correlation value or statistical finding for experiment {idx}?"
            elif cat == "Contracts":
                query = f"Identify the clause, liabilities, and obligations for entity {idx}"
            elif cat == "Invoices":
                query = f"Review total amount, dates, and line item statistics for invoice {idx}"
            elif cat == "Forms":
                query = f"Extract form field values and layout mapping for box {idx}"
            elif cat == "Technical Manuals":
                query = f"What is the system configuration or table caption description {idx}?"
            else:
                query = f"Locate section header and structural references in mixed page {idx}"

            questions.append({
                "question": query,
                "document_id": "doc123",
                "expected_chunk_ids": ["chunk-0"],
                "expected_graph_nodes": ["node-p1" if idx % 2 == 0 else "node-h1"],
                "expected_entities": ["Google"],
                "expected_tables": ["tbl-1"] if cat in ["Invoices", "Technical Manuals", "Research Papers"] else [],
                "difficulty": difficulty,
                "category": cat
            })

    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(output_dir, "metadata.json")
    os.makedirs(output_dir, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"questions": questions}, f, indent=2)

    print(f"Generated {len(questions)} E2E benchmark questions in: {output_path}")

if __name__ == "__main__":
    generate_questions()
