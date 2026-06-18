import requests
import time
import sys

API_URL = 'http://localhost:5000'
HEADERS = {'X-API-Key': 'dev_secret_api_key'}

def upload_and_wait(filepath):
    print(f'\n--- Uploading {filepath} ---')
    try:
        with open(filepath, 'rb') as f:
            res = requests.post(f'{API_URL}/files/upload', files={'file': f}, headers=HEADERS)
        if res.status_code != 200:
            print('Upload failed:', res.text)
            return
        
        data = res.json()
        pipeline_id = data.get('pipeline_id')
        if not pipeline_id:
            print('No pipeline ID returned')
            return
            
        print('Waiting for processing...')
        for i in range(25):
            time.sleep(2)
            res = requests.get(f'{API_URL}/pipelines/{pipeline_id}', headers=HEADERS)
            pipe_data = res.json()
            if pipe_data.get('status') in ['completed', 'failed']:
                break
                
        print(f'Final Status: {pipe_data.get("status")}')
        
        res = requests.get(f'{API_URL}/pipelines/{pipeline_id}/timeline', headers=HEADERS)
        timeline = res.json()
        preprocess_task_id = None
        for item in timeline:
            if item.get('task_type') == 'preprocess_document':
                preprocess_task_id = item.get('id')
                break
                
        if preprocess_task_id:
            res = requests.get(f'{API_URL}/tasks/{preprocess_task_id}/details', headers=HEADERS)
            task_details = res.json()
            print('--- Worker Logs ---')
            for log in task_details.get('logs', []):
                print(f"[{log['event_type']}] {log['message']}")
        else:
            print('Preprocess task not found in timeline.')
            
    except Exception as e:
        print('Error:', e)

upload_and_wait(r'test_data\category_A_simple.pdf')
upload_and_wait(r'test_data\category_C_large.pdf')

