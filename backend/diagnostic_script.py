import sys
import os

# Add backend to path to allow absolute imports like "services.document_preprocessor"
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.document_preprocessor import evaluate_document
import json

filepath = r'D:\Projects\task-schedular\backend\storage\uploads\2_PBL_Synopsis_1.pdf'
report = evaluate_document(filepath)
print('document_type:', report.document_type)
print('extractable_text_ratio:', report.extractable_text_ratio)
print('needs_enhancement:', report.needs_enhancement)
print('enhancement_flags:', report.enhancement_flags)
print('warnings:', report.warnings)
