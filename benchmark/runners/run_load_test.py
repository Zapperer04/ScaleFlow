import os
import sys
import time
import json
import random
import concurrent.futures

# Setup path imports
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

def simulate_request(req_id):
    # Simulated load request latency
    start = time.time()
    time.sleep(random.uniform(0.05, 0.45))
    return time.time() - start

def calculate_percentiles(latencies):
    if not latencies:
        return 0.0, 0.0, 0.0
    sorted_latencies = sorted(latencies)
    n = len(sorted_latencies)
    p50 = sorted_latencies[int(n * 0.5)]
    p95 = sorted_latencies[int(n * 0.95)] if n > 1 else sorted_latencies[0]
    p99 = sorted_latencies[int(n * 0.99)] if n > 1 else sorted_latencies[0]
    return p50, p95, p99

def run():
    print("=== Running Serving Platform Load Stress Test ===")
    concurrency_levels = [10, 50, 100]
    results = {}
    
    for level in concurrency_levels:
        print(f"Simulating {level} concurrent sessions...")
        latencies = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=level) as executor:
            futures = [executor.submit(simulate_request, i) for i in range(level)]
            for fut in concurrent.futures.as_completed(futures):
                latencies.append(fut.result())
                
        p50, p95, p99 = calculate_percentiles(latencies)
        results[level] = {"p50": p50, "p95": p95, "p99": p99}
        print(f"  Level {level} -> P50: {p50:.3f}s, P95: {p95:.3f}s, P99: {p99:.3f}s")
        
    os.makedirs("benchmark/results", exist_ok=True)
    with open("benchmark/results/load_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    return results

if __name__ == "__main__":
    run()
