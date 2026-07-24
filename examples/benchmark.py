#!/usr/bin/env python3
"""
MR-RAG v1.0 Client Example: Run Benchmark Suite
"""
import sys
import os
import subprocess

def trigger_benchmark():
    workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    python_exec = os.path.join(workspace_dir, "backend", "venv", "bin", "python")
    benchmark_script = os.path.join(workspace_dir, "benchmark", "run_benchmark.py")
    
    if not os.path.exists(python_exec):
        python_exec = "python3"
        
    print(f"Executing benchmark script using {python_exec}...")
    try:
        res = subprocess.run([python_exec, benchmark_script], cwd=workspace_dir, capture_output=True, text=True, check=True)
        print(res.stdout)
        print("Benchmark completed successfully.")
        
        manifest_path = os.path.join(workspace_dir, "benchmark", "results", "manifest.json")
        if os.path.exists(manifest_path):
            with open(manifest_path, "r") as f:
                import json
                manifest = json.load(f)
                print("\n=== BENCHMARK MANIFEST ===")
                print(f"Status: {manifest.get('status')}")
                print(f"Git Commit: {manifest.get('metadata', {}).get('git_commit')}")
                print("Hybrid Recall@5:", manifest.get("summary_metrics", {}).get("Hybrid", {}).get("recall"))
                print("Hybrid MRR:", manifest.get("summary_metrics", {}).get("Hybrid", {}).get("mrr"))
        else:
            print("Manifest results file not found.")
    except subprocess.CalledProcessError as e:
        print(f"Benchmark execution failed: {e.stderr}")

if __name__ == "__main__":
    trigger_benchmark()
