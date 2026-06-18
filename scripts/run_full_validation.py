import requests
import json
import time
import os
import collections

API_URL = "http://localhost:5000"
HEADERS = {"X-API-Key": "dev_secret_api_key"}

FILES_TO_TEST = [
    "216_ML_Notes.pdf",
    "214_Bhoomimitra_patent.pdf",
    "93_photographed_notes.pdf",
    "9_category_B_academic.pdf",
    "8_category_C_large.pdf",
    "9_category_D_scanned.pdf",
    "6_category_A_simple.pdf",
    "92_category_E_malformed.pdf",
    "84_Kaustav_OOPsAssign2.pdf",
    "3_The_Money_Changers_--_Arthur_Hailey_--_1975_--_Bantam_Books_--_9788129108074_--_.pdf"
]

report = {
    "runs": [],
    "total_pass": 0,
    "total_fail": 0,
    "total_lease_expiries": 0,
    "total_recoveries": 0,
    "total_fencing_conflicts": 0,
    "total_queue_healer": 0,
    "stage_latencies": collections.defaultdict(list),
    "total_retries": 0,
}

for idx, filename in enumerate(FILES_TO_TEST):
    file_path = f"backend/storage/uploads/{filename}"
    print(f"\n--- RUN {idx+1}/10: {filename} ---")
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        continue

    with open(file_path, 'rb') as f:
        res = requests.post(
            f"{API_URL}/files/upload",
            files={"file": f},
            data={"priority": "high", "pipeline_type": "document_processing_demo"},
            headers=HEADERS
        )
    
    if res.status_code != 201:
        print(f"Upload failed: {res.status_code}")
        continue
        
    pipeline_id = res.json().get('pipeline_id')
    print(f"Pipeline created: #{pipeline_id}")
    
    run_stats = {
        "filename": filename,
        "pipeline_id": pipeline_id,
        "status": "running",
        "transitions": [],
        "tasks": {},
        "recoveries": 0,
        "lease_expiries": 0,
        "fencing_conflicts": 0,
        "queue_healer": 0,
        "retries": 0
    }
    
    task_states = {}
    
    while True:
        time.sleep(1.5)
        try:
            p_res = requests.get(f"{API_URL}/pipelines/{pipeline_id}", headers=HEADERS)
            if p_res.status_code != 200: continue
            
            data = p_res.json()
            pipeline = data['pipeline']
            tasks = data.get('tasks', [])
            
            for t in tasks:
                tid = t['id']
                if tid not in task_states:
                    task_states[tid] = {'status': None, 'recovered': 0, 'retries': 0, 'duration': 0}
                    run_stats["tasks"][t['type']] = {'worker': t.get('assigned_worker_id'), 'lease': t.get('lease_token')}
                    
                current_status = t['status']
                
                if current_status != task_states[tid]['status']:
                    run_stats["transitions"].append(f"[TASK #{tid}] {t['type']} -> {current_status}")
                    task_states[tid]['status'] = current_status
                
                # Check for recovering state
                if current_status == 'recovering':
                    run_stats["recoveries"] += 1
                    report["total_recoveries"] += 1
                    
                # Track duration
                if t.get('execution_duration'):
                    task_states[tid]['duration'] = t['execution_duration']
                    
                # Track retries
                if t.get('retry_count', 0) > task_states[tid]['retries']:
                    new_retries = t['retry_count'] - task_states[tid]['retries']
                    run_stats["retries"] += new_retries
                    report["total_retries"] += new_retries
                    task_states[tid]['retries'] = t['retry_count']
                    
                # Error check
                err = t.get('error_message', '')
                if err:
                    if 'lease expired' in err.lower():
                        run_stats["lease_expiries"] += 1
                        report["total_lease_expiries"] += 1
                    if 'fencing' in err.lower() or 'stale' in err.lower() or 'conflict' in err.lower():
                        run_stats["fencing_conflicts"] += 1
                        report["total_fencing_conflicts"] += 1
                        
            if pipeline['status'] in ['completed', 'failed']:
                run_stats['status'] = pipeline['status']
                if pipeline['status'] == 'completed':
                    report['total_pass'] += 1
                else:
                    report['total_fail'] += 1
                break
                
        except Exception as e:
            print(f"Error polling: {e}")
            
    # Record stage latencies
    for t in tasks:
        stage = t['type']
        dur = t.get('execution_duration', 0)
        if dur > 0:
            report['stage_latencies'][stage].append(dur)
            
    # For large document, extract specific stats
    if "Money_Changers" in filename:
        print(f"--- LARGE DOCUMENT STRESS TEST RESULTS ---")
        total_time = sum(task_states[tid]['duration'] for tid in task_states)
        print(f"Total Processing Time: {total_time}s")
        print(f"Final Status: {run_stats['status']}")
        for t in tasks:
            if t['type'] == 'parse_document':
                print(f"OCR Duration: {t.get('execution_duration')}s")
            elif t['type'] == 'generate_embeddings':
                print(f"Embedding Duration: {t.get('execution_duration')}s")
                try:
                    if t.get('output_artifact_ids'):
                        art_id = json.loads(t['output_artifact_ids'])[0]
                        print(f"Chunk Count: See Artifact #{art_id}")
                except: pass
            print(f"Task {t['type']} renewals: {t.get('lease_renewal_count', 0)}")
            
    report['runs'].append(run_stats)

with open('reliability_suite_results.json', 'w') as f:
    json.dump(report, f, indent=2)
    
print("\n--- VALIDATION COMPLETE ---")
print(f"Total Passed: {report['total_pass']}/10")
