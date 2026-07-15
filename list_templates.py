import sys, os
sys.path.append(os.path.abspath('backend'))
from orchestrator.dag_builder import TEMPLATES
print(list(TEMPLATES.keys()))
