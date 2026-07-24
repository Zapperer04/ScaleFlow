import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from runners.run_profiling import run

if __name__ == "__main__":
    run()
