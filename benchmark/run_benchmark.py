import os
import sys

# Ensure root path is correct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from runners.run_benchmark import run

if __name__ == "__main__":
    run()
