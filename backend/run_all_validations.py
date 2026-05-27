import os
import sys
import time
import subprocess

def run_suite(script_name):
    print(f"\n{'='*60}")
    print(f"Executing: {script_name}")
    print(f"{'='*60}")
    
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    try:
        result = subprocess.run([sys.executable, script_path], check=True)
        print(f"[{script_name}] SUCCESS")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[{script_name}] FAILED with exit code {e.returncode}")
        return False

def main():
    print("\n" + "#"*60)
    print("FINAL STABILITY VALIDATION")
    print("#"*60)
    
    suites = [
        {"name": "TXT Determinism Validation", "script": os.path.join(os.path.dirname(os.path.dirname(__file__)), "run_20_tests.py")},
        {"name": "PDF Fallback Validation", "script": os.path.join(os.path.dirname(__file__), "validate_pdf_pipeline.py")},
        {"name": "Retrieval Validation", "script": os.path.join(os.path.dirname(__file__), "validate_retrieval_quality.py")}
    ]
    
    all_passed = True
    for s in suites:
        print(f"\n{'='*60}")
        print(f"Executing: {s['name']} ({s['script']})")
        print(f"{'='*60}")
        try:
            result = subprocess.run([sys.executable, s['script']], check=True)
            print(f"[{s['name']}] SUCCESS")
        except subprocess.CalledProcessError as e:
            print(f"[{s['name']}] FAILED with exit code {e.returncode}")
            all_passed = False
            
    print("\n" + "#"*60)
    if all_passed:
        print("ALL VALIDATION SUITES PASSED! Platform is stable.")
        sys.exit(0)
    else:
        print("ONE OR MORE VALIDATION SUITES FAILED. Check logs.")
        sys.exit(1)

if __name__ == "__main__":
    main()
