import re
import os

with open(r'd:\Projects\task-schedular\backend\worker.py', encoding='utf-8') as f:
    lines = f.readlines()
pattern = re.compile(r'preprocess|enhancement|run_enhancement|needs_enhancement', re.IGNORECASE)
for i, line in enumerate(lines):
    if pattern.search(line):
        print(f'{i+1}: {line.rstrip()}')
