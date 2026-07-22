import os
import json
from typing import Dict, Any

class ReportGenerator:
    def __init__(self, output_dir: str = None):
        if output_dir is None:
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
            output_dir = os.path.join(current_dir, "reports")
        os.makedirs(output_dir, exist_ok=True)
        self.output_dir = output_dir

    def generate_reports(self, eval_data: Dict[str, Any]):
        # Write retrieval_metrics.json
        metrics_json_path = os.path.join(self.output_dir, "retrieval_metrics.json")
        with open(metrics_json_path, "w", encoding="utf-8") as f:
            json.dump(eval_data.get("overall_metrics", {}), f, indent=2)

        # Write retrieval_dashboard.json
        dashboard_json_path = os.path.join(self.output_dir, "retrieval_dashboard.json")
        dashboard_data = {
            "overall_metrics": eval_data.get("overall_metrics", {}),
            "summary": "Hybrid Multi-Representation Retrieval Performance Analysis"
        }
        with open(dashboard_json_path, "w", encoding="utf-8") as f:
            json.dump(dashboard_data, f, indent=2)

        # Write retrieval_benchmark.md
        benchmark_md_path = os.path.join(self.output_dir, "retrieval_benchmark.md")
        with open(benchmark_md_path, "w", encoding="utf-8") as f:
            f.write("# Retrieval Benchmark Report\n\n")
            f.write("## Overall Metrics Summary\n\n")
            metrics = eval_data.get("overall_metrics", {})
            for key, val in metrics.items():
                f.write(f"- **{key}**: {val:.4f}\n")
            f.write("\n## E2E Query Evaluation\n\n")
            for res in eval_data.get("benchmark_results", []):
                q = res["question_data"]["question"]
                f.write(f"### Query: {q}\n")
                f.write(f"- **Category**: {res['question_data']['category']}\n")
                f.write(f"- **Latency**: {res['latency']:.4f}s\n")
                f.write(f"- **Token Usage**: {res['token_usage']} words\n\n")

        # Write retrieval_ablation.md
        ablation_md_path = os.path.join(self.output_dir, "retrieval_ablation.md")
        with open(ablation_md_path, "w", encoding="utf-8") as f:
            f.write("# Retrieval Ablation Study\n\n")
            f.write("Comparison of different retrieval experts configuration:\n\n")
            f.write("| Expert Config | Recall@5 | Precision@5 | Latency (s) | Token Usage |\n")
            f.write("| --- | --- | --- | --- | --- |\n")
            
            # Extract configuration comparisons from first question's ablation result
            first_q_ab = list(eval_data.get("ablation_results", {}).values())[0] if eval_data.get("ablation_results") else {}
            for name, details in first_q_ab.items():
                metrics_dict = details.get("metrics", {})
                recall = metrics_dict.get("recall_5", 0.0)
                precision = metrics_dict.get("precision_5", 0.0)
                f.write(f"| {name} | {recall:.4f} | {precision:.4f} | {details['latency']:.4f} | {details['token_usage']} |\n")

        # Write retrieval_explainability.md
        explain_md_path = os.path.join(self.output_dir, "retrieval_explainability.md")
        with open(explain_md_path, "w", encoding="utf-8") as f:
            f.write("# Retrieval Explainability Log\n\n")
            for res in eval_data.get("benchmark_results", []):
                q = res["question_data"]["question"]
                f.write(f"### Query: {q}\n")
                f.write(f"- **Agreement Count**: {res['agreement_count']} experts\n")
                f.write("- **Retrieved Chunks**: " + ", ".join(res["retrieved_chunks"]) + "\n\n")

        # Write retrieval_latency.md
        latency_md_path = os.path.join(self.output_dir, "retrieval_latency.md")
        with open(latency_md_path, "w", encoding="utf-8") as f:
            f.write("# Latency Performance Analysis\n\n")
            f.write("Detailed runtime profiling across E2E stages:\n\n")
            for res in eval_data.get("benchmark_results", []):
                q = res["question_data"]["question"]
                f.write(f"### Query: {q}\n")
                details = res["latency_details"]
                f.write(f"- **Total Time**: {details['total']:.4f}s\n")
                f.write(f"- **Fusion Engine**: {details['fusion']:.4f}s\n")
                f.write(f"- **Reranker**: {details['rerank']:.4f}s\n")
                f.write(f"- **Context Optimizer**: {details['optimizer']:.4f}s\n")
                f.write("- **Experts**:\n")
                for exp_name, exp_lat in details["experts"].items():
                    f.write(f"  - *{exp_name}*: {exp_lat:.4f}s\n")
                f.write("\n")
