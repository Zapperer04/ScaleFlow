import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from services.document_retrieval.evaluation.report_generator import ReportGenerator

def test_report_generation(tmp_path):
    output_dir = str(tmp_path)
    generator = ReportGenerator(output_dir=output_dir)
    
    eval_data = {
        "overall_metrics": {
            "recall_5": 1.0,
            "precision_5": 0.8,
            "mrr": 1.0,
            "ndcg_5": 0.95
        },
        "benchmark_results": [
            {
                "question_data": {
                    "question": "What is Table 1?",
                    "category": "Technical Manuals"
                },
                "retrieved_chunks": ["chunk-0"],
                "retrieved_nodes": [],
                "retrieved_entities": [],
                "retrieved_tables": [],
                "latency": 0.05,
                "token_usage": 120,
                "agreement_count": 2,
                "latency_details": {
                    "total": 0.05,
                    "fusion": 0.001,
                    "rerank": 0.002,
                    "optimizer": 0.001,
                    "experts": {"vector": 0.04}
                }
            }
        ],
        "ablation_results": {
            "What is Table 1?": {
                "Vector-Only": {
                    "latency": 0.04,
                    "token_usage": 100,
                    "metrics": {"recall_5": 1.0, "precision_5": 0.8}
                }
            }
        }
    }
    
    generator.generate_reports(eval_data)
    
    assert os.path.exists(os.path.join(output_dir, "retrieval_metrics.json"))
    assert os.path.exists(os.path.join(output_dir, "retrieval_benchmark.md"))
    assert os.path.exists(os.path.join(output_dir, "retrieval_ablation.md"))
    assert os.path.exists(os.path.join(output_dir, "retrieval_explainability.md"))
    assert os.path.exists(os.path.join(output_dir, "retrieval_latency.md"))
    assert os.path.exists(os.path.join(output_dir, "retrieval_dashboard.json"))
