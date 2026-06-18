with open(r'd:\Projects\task-schedular\backend\services\document_preprocessor.py', encoding='utf-8') as f:
    content = f.read()
start = content.find('def run_enhancement_pipeline')
end = content.find('def ', start + 1)
if end == -1: end = len(content)
print(content[start:end])
