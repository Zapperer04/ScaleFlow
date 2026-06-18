import sys
import os
import logging
sys.path.append(r'd:\Projects\task-schedular\backend')

# Configure basic logging to see worker output
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

from backend.worker import handle_preprocess_document

files_to_test = [
    r'D:\Projects\task-schedular\backend\storage\uploads\2_PBL_Synopsis_1.pdf',
    r'D:\Projects\task-schedular\backend\storage\uploads\9_category_D_scanned.pdf'
]

for file in files_to_test:
    print(f"\n--- Testing file: {os.path.basename(file)} ---")
    payload = {"file_path": file, "task_id": 9999}
    try:
        report = handle_preprocess_document(payload, {})
        print("\nResult Report:")
        print(report)
    except Exception as e:
        print(f"Error testing {file}: {e}")
