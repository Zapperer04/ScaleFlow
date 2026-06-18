import sys
import os
sys.path.append(r'd:\Projects\task-schedular\backend')
from services.document_preprocessor import evaluate_document

filepath = r'd:\Projects\task-schedular\test_data\category_D_scanned.pdf'
print('Evaluating document...')
report = evaluate_document(filepath, trace_fn=lambda msg: print(msg))
print('Report generated:', report)
