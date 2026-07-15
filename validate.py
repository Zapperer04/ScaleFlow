import sys
import os

sys.path.append(os.path.abspath('backend'))
try:
    from task_registry import validate_registry
    validate_registry()
    print('Registry Validation: SUCCESS')
except Exception as e:
    print(f'Registry Validation: FAILED - {e}')
