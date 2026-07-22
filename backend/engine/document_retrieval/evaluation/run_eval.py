import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from engine.document_pipeline.storage.storage import DocumentStore
from engine.document_retrieval.orchestrator import RetrievalOrchestrator
from engine.document_retrieval.evaluation.evaluator import RetrievalEvaluator
from engine.document_retrieval.evaluation.report_generator import ReportGenerator

def generate_mock_index(store: DocumentStore, doc_id: str):
    # Embeddings
    store.save_json(doc_id, "embeddings/vectors.json", [
        {"chunk_id": "chunk-0", "vector": [0.1] * 768, "metadata": {"type": "chunk"}},
        {"chunk_id": "node-h1", "vector": [0.9] * 768, "metadata": {"type": "heading"}}
    ])
    # Graph
    store.save_json(doc_id, "graph/nodes.json", [
        {"id": "node-h1", "type": "Heading", "text": "Introduction"},
        {"id": "node-p1", "type": "Paragraph", "text": "This relates to Table 1"}
    ])
    store.save_json(doc_id, "graph/edges.json", [
        {"source": "node-h1", "target": "node-p1", "type": "parent_child"}
    ])
    # Entities
    store.save_json(doc_id, "entities/entities.json", {
        "entities": [
            {
                "id": "ent-1",
                "name": "Google",
                "type": "Organization",
                "normalized_value": "Google",
                "aliases": ["Google Corp"],
                "graph_node_ids": ["node-p1"]
            }
        ],
        "edges": []
    })
    # Tables
    store.save_json(doc_id, "tables/tables.json", [
        {
            "id": "tbl-1",
            "caption": "Table 1",
            "headers": ["A", "B"],
            "graph_node_id": "node-p1"
        }
    ])
    # Layout
    store.save_json(doc_id, "layout/layout.json", {
        "visual_blocks": {
            "node-p1": {
                "page": 1,
                "type": "paragraph",
                "bbox": {"ymin": 0.8, "xmin": 0.8, "ymax": 0.9, "xmax": 0.9}
            }
        }
    })
    # Chunks
    store.save_json(doc_id, "chunks/chunks.json", [
        {
            "chunk_id": "chunk-0",
            "text": "This is standard introduction text mentioning Google Corp and Table 1 statistics.",
            "graph_node_ids": ["node-h1", "node-p1"],
            "entities": ["Google"],
            "page_range": [1],
            "best_for": ["semantic", "definition"],
            "importance_score": 1.2
        }
    ])

def main():
    store = DocumentStore()
    doc_id = "doc123"
    
    print(f"Creating mock document index data for '{doc_id}' in storage...")
    generate_mock_index(store, doc_id)

    # Mock embed_text to return [0.1] * 768 during evaluation queries
    import engine.document_retrieval.query_understanding as qu_mod
    qu_mod.embed_text = lambda text: [0.1] * 768

    print("Running E2E Retrieval Evaluator...")
    orchestrator = RetrievalOrchestrator(store=store)
    evaluator = RetrievalEvaluator(orchestrator=orchestrator)
    eval_data = evaluator.evaluate_all()

    print("Generating benchmark reports in reports/ directory...")
    report_gen = ReportGenerator()
    report_gen.generate_reports(eval_data)
    
    print("E2E Evaluation run completed successfully!")

if __name__ == "__main__":
    main()
