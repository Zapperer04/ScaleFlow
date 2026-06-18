import requests
import time
import os

headers = {'X-API-Key': 'dev_secret_api_key'}

# Locate the resume file (root of workspace or backend uploads)
resume_path = 'backend/storage/uploads/KaustavKumar_Resume.pdf'
if not os.path.exists(resume_path):
    resume_path = 'KaustavKumar_Resume.pdf'

print(f"Uploading resume from: {resume_path}")
with open(resume_path, 'rb') as f:
    r = requests.post('http://localhost:5000/files/upload', files={'file': f}, headers=headers)

if r.status_code != 201:
    print("Upload failed:", r.status_code, r.text)
    exit(1)

pipeline_id = r.json()['pipeline_id']
print(f'Ingestion pipeline: {pipeline_id}')

print('Waiting 60 seconds for ingestion pipeline to complete...')
time.sleep(60)

print('Sending query pipeline request...')
r = requests.post('http://localhost:5000/query-pipelines', json={
    'query': 'what projects has this candidate built',
    'pipeline_id': pipeline_id,  # scope to resume only
    'top_k': 3
}, headers=headers)

if r.status_code != 201:
    print("Query pipeline creation failed:", r.status_code, r.text)
    exit(1)

qp_id = r.json()['pipeline_id']
print(f'Query pipeline ID: {qp_id}')

print('Waiting 15 seconds for query pipeline to finish...')
time.sleep(15)

r = requests.get(f'http://localhost:5000/query-pipelines/{qp_id}/answer', headers=headers)
data = r.json()

print('\n--- Raw Data returned ---')
print(data)

print('\n--- Formatted Verification Results ---')
# Check direct keys or nested keys depending on API structure
answer = data.get('answer') or data.get('final_answer', {}).get('answer', 'N/A')
print('Answer:', answer[:500])

chunks = data.get('retrieved_chunks') or data.get('retrieved_context', {}).get('results', [])
for chunk in chunks:
    print(f"Score: {chunk.get('rerank_score', 'N/A'):.4f} | Section: {chunk.get('section')} | Text: {chunk.get('chunk_text', '')[:80]}")
