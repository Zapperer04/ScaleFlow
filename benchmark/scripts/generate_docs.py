import os
import shutil

def run():
    os.makedirs("docs", exist_ok=True)
    
    # Map the generated reports to the final doc paths
    shutil.copy("reports/benchmark.md", "docs/Benchmark_Report.md")
    shutil.copy("reports/profiling.md", "docs/Performance_Report.md")
    shutil.copy("reports/scalability.md", "docs/Scalability_Report.md")
    shutil.copy("reports/production_readiness.md", "docs/Production_Qualification.md")
    shutil.copy("reports/failure_analysis.md", "docs/Failure_Analysis.md")
    shutil.copy("reports/optimization_recommendations.md", "docs/Optimization_Guide.md")
    
    print("Documentation files generated under docs/ successfully.")

if __name__ == "__main__":
    run()
