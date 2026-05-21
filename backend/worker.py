import time
import requests
import redis
import json
import os
import random
import threading
import traceback
from datetime import datetime

def load_env():
    try:
        with open('.env') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, val = line.strip().split('=', 1)
                    os.environ.setdefault(key.strip(), val.strip())
    except FileNotFoundError:
        pass

load_env()

API_URL = os.getenv("API_URL", "http://localhost:5000")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
WORKER_ID = os.getenv("WORKER_ID", "worker-1")
API_KEY = os.getenv("API_KEY", "dev_secret_api_key")

HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

print(f"[{WORKER_ID}] Initializing Redis client: host={REDIS_HOST}, port={REDIS_PORT}", flush=True)
redis_client = redis.Redis(
    host=REDIS_HOST, 
    port=REDIS_PORT, 
    decode_responses=True,
    socket_timeout=5,
    socket_connect_timeout=5
)

# Standard list of queue names
PRIORITY_QUEUES = ['task_queue_high', 'task_queue_medium', 'task_queue_low']

worker_state = {
    'status': 'idle',
    'current_task_id': None,
    'tasks_completed': 0,
    'tasks_failed': 0,
    'last_action': 'Initializing worker'
}

def send_heartbeat():
    """Send heartbeat to API every 10 seconds"""
    while True:
        try:
            payload = {
                'worker_id': WORKER_ID,
                'status': worker_state['status'],
                'current_task_id': worker_state['current_task_id'],
                'tasks_completed': worker_state['tasks_completed'],
                'tasks_failed': worker_state['tasks_failed'],
                'last_action': worker_state['last_action']
            }
            res = requests.post(f"{API_URL}/workers/heartbeat", 
                        json=payload, headers=HEADERS, timeout=5)
            if res.status_code != 200:
                print(f"[{WORKER_ID}] Heartbeat status error: {res.status_code} - {res.text}", flush=True)
        except Exception as e:
            print(f"[{WORKER_ID}] Heartbeat connection failed: {e}", flush=True)
        time.sleep(10)

try:
    from task_registry import TASK_REGISTRY
except ImportError:
    TASK_REGISTRY = {}

def handle_send_email(payload):
    print(f"[{WORKER_ID}]   → Sending email to {payload.get('to')}", flush=True)
    if payload.get('cc'):
        print(f"[{WORKER_ID}]   → CC: {payload.get('cc')}", flush=True)
    time.sleep(2)
    print(f"[{WORKER_ID}]   ✓ Email sent!", flush=True)

def handle_process_video(payload):
    print(f"[{WORKER_ID}]   → Processing video {payload.get('file')}", flush=True)
    if payload.get('format'):
        print(f"[{WORKER_ID}]   → Format: {payload.get('format')}", flush=True)
    if payload.get('resolution'):
        print(f"[{WORKER_ID}]   → Resolution: {payload.get('resolution')}", flush=True)
    time.sleep(3)
    print(f"[{WORKER_ID}]   ✓ Video processed!", flush=True)

def handle_generate_report(payload):
    print(f"[{WORKER_ID}]   → Generating report: {payload.get('report_type')}", flush=True)
    if payload.get('format'):
        print(f"[{WORKER_ID}]   → Format: {payload.get('format')}", flush=True)
    time.sleep(4)
    print(f"[{WORKER_ID}]   ✓ Report generated!", flush=True)

def handle_data_backup(payload):
    print(f"[{WORKER_ID}]   → Backing up {payload.get('database')}", flush=True)
    time.sleep(5)
    print(f"[{WORKER_ID}]   ✓ Backup completed!", flush=True)

def handle_image_processing(payload):
    print(f"[{WORKER_ID}]   → Processing image: {payload.get('image_path')}", flush=True)
    time.sleep(3)
    print(f"[{WORKER_ID}]   ✓ Image processed!", flush=True)

def handle_send_notification(payload):
    print(f"[{WORKER_ID}]   → Sending notification to {payload.get('user_id')}", flush=True)
    time.sleep(1)
    print(f"[{WORKER_ID}]   ✓ Notification sent!", flush=True)

def handle_run_ml_model(payload):
    print(f"[{WORKER_ID}]   → Running ML model: {payload.get('model_name')}", flush=True)
    time.sleep(6)
    print(f"[{WORKER_ID}]   ✓ Model executed!", flush=True)

def handle_webhook_trigger(payload):
    print(f"[{WORKER_ID}]   → Triggering webhook: {payload.get('url')}", flush=True)
    time.sleep(2)
    print(f"[{WORKER_ID}]   ✓ Webhook triggered!", flush=True)

HANDLER_MAP = {
    "send_email": handle_send_email,
    "process_video": handle_process_video,
    "generate_report": handle_generate_report,
    "data_backup": handle_data_backup,
    "image_processing": handle_image_processing,
    "send_notification": handle_send_notification,
    "run_ml_model": handle_run_ml_model,
    "webhook_trigger": handle_webhook_trigger
}

def execute_task(task):
    """Simulate doing the actual work - with random failures for testing retry"""
    task_type = task['type']
    task_data = task['data']
    task_id = task['id']
    retry_count = task.get('retry_count', 0)
    priority = task.get('priority', 'medium')
    
    print(f"[{WORKER_ID}] [{datetime.now().strftime('%H:%M:%S')}] Executing task {task_id}: {task_type} [Priority: {priority.upper()}] (Attempt {retry_count + 1})", flush=True)
    
    # Check for simulate_hang_seconds in payload
    simulate_hang_seconds = task_data.get('simulate_hang_seconds')
    if simulate_hang_seconds is not None:
        try:
            hang_time = float(simulate_hang_seconds)
            print(f"[{WORKER_ID}]   ⏳ [Simulation] Hanging task for {hang_time} seconds...", flush=True)
            time.sleep(hang_time)
            print(f"[{WORKER_ID}]   ⏳ [Simulation] Wake up after hang!", flush=True)
        except (ValueError, TypeError):
            print(f"[{WORKER_ID}]   ⚠ Invalid simulate_hang_seconds value: {simulate_hang_seconds}", flush=True)

    if random.random() < 0.1 and retry_count < 2:
        print(f"[{WORKER_ID}]   ✗ Task failed! Will retry...", flush=True)
        raise Exception(f"Simulated failure for task {task_id}")
    
    # Check in handler map
    handler = HANDLER_MAP.get(task_type)
    if not handler:
        # Check task registry for handler name mapping fallback
        registry_info = TASK_REGISTRY.get(task_type, {})
        handler_name = registry_info.get("handler_name")
        if handler_name:
            handler = globals().get(handler_name)
            
    if handler:
        handler(task_data)
    else:
        print(f"[{WORKER_ID}]   ⚠ Unknown task type / handler: {task_type}", flush=True)

def get_next_task():
    """Get next task from highest priority queue that has tasks"""
    try:
        # Atomic priority-based blocking pop using BRPOP
        result = redis_client.brpop(PRIORITY_QUEUES, timeout=5)
        if result:
            return result
    except redis.exceptions.ConnectionError as ce:
        print(f"[{WORKER_ID}] Redis connection error during brpop: {ce}", flush=True)
        raise ce
    except redis.exceptions.TimeoutError:
        # Socket timeout during blocking pop, safe to loop
        pass
    except Exception as e:
        print(f"[{WORKER_ID}] Error in get_next_task: {e}", flush=True)
        traceback.print_exc()
    return None

def worker_loop():
    worker_state['last_action'] = 'Verifying Redis'
    print(f"[{WORKER_ID}] Worker started! Verifying Redis connection...", flush=True)
    try:
        redis_client.ping()
        print(f"[{WORKER_ID}] Connected to Redis successfully!", flush=True)
    except Exception as e:
        print(f"[{WORKER_ID}] CRITICAL: Failed to connect to Redis: {e}", flush=True)
    
    print(f"[{WORKER_ID}] PRIORITY_QUEUES type: {type(PRIORITY_QUEUES)}, value: {PRIORITY_QUEUES}", flush=True)
    print(f"[{WORKER_ID}] Listening on queue names: {PRIORITY_QUEUES}", flush=True)
    print(f"[{WORKER_ID}] Heartbeat enabled - sending to {API_URL}/workers/heartbeat every 10s", flush=True)
    
    heartbeat_thread = threading.Thread(target=send_heartbeat, daemon=True)
    heartbeat_thread.start()
    
    while True:
        try:
            worker_state['last_action'] = 'Waiting for task'
            print(f"[{WORKER_ID}] Waiting for task...", flush=True)
            result = get_next_task()
            
            if result:
                queue_name, task_id = result
                # Decode bytes to string if needed
                task_id = task_id.decode() if isinstance(task_id, bytes) else str(task_id)
                worker_state['last_action'] = f"Received task #{task_id}"
                print(f"[{WORKER_ID}] Received task_id {task_id} from queue {queue_name}", flush=True)
                
                worker_state['last_action'] = f"Claiming task #{task_id}"
                print(f"[{WORKER_ID}] Claiming task #{task_id} from API...", flush=True)
                response = requests.post(f"{API_URL}/tasks/{task_id}/claim", json={'worker_id': WORKER_ID}, headers=HEADERS, timeout=5)
                
                if response.status_code != 200:
                    worker_state['last_action'] = f"Failed to claim task #{task_id}"
                    print(f"[{WORKER_ID}] Claim failed: {response.status_code} - {response.text}", flush=True)
                    continue
                    
                task = response.json()
                lease_token = task.get('lease_token')
                
                worker_state['last_action'] = f"Executing task #{task_id}"
                print(f"[{WORKER_ID}] Starting task {task_id} ({task.get('type')})...", flush=True)
                worker_state['status'] = 'busy'
                worker_state['current_task_id'] = task_id
                
                try:
                    retry_count = task.get('retry_count', 0)
                    if retry_count > 0:
                        delay = min(2 ** retry_count, 30)
                        worker_state['last_action'] = f"Backing off task #{task_id} for {delay}s"
                        print(f"[{WORKER_ID}] Waiting {delay}s backoff before retry...", flush=True)
                        time.sleep(delay)
                        worker_state['last_action'] = f"Executing task #{task_id}"
                    
                    execute_task(task)
                    
                    res_complete = requests.patch(f"{API_URL}/tasks/{task_id}", 
                                 json={'status': 'completed', 'worker_id': WORKER_ID, 'lease_token': lease_token}, headers=HEADERS, timeout=5)
                    if res_complete.status_code != 200:
                        print(f"[{WORKER_ID}] Warning: failed to patch status to completed: {res_complete.status_code} - {res_complete.text}", flush=True)
                        if res_complete.status_code == 409:
                            print(f"[{WORKER_ID}] ⚠️ Task completion rejected: lease expired or owned by another worker.", flush=True)
                    else:
                        worker_state['tasks_completed'] += 1
                        
                    worker_state['last_action'] = f"Completed task #{task_id}"
                    print(f"[{WORKER_ID}] Completed task {task_id} successfully!", flush=True)
                    
                except Exception as e:
                    worker_state['last_action'] = f"Failed task #{task_id}"
                    print(f"[{WORKER_ID}] Failed task {task_id}: {str(e)}", flush=True)
                    res_fail = requests.patch(f"{API_URL}/tasks/{task_id}", 
                                 json={
                                     'status': 'failed',
                                     'error_message': str(e),
                                     'worker_id': WORKER_ID,
                                     'lease_token': lease_token
                                 }, headers=HEADERS, timeout=5)
                    if res_fail.status_code != 200:
                        print(f"[{WORKER_ID}] Warning: failed to patch status to failed: {res_fail.status_code} - {res_fail.text}", flush=True)
                        if res_fail.status_code == 409:
                            print(f"[{WORKER_ID}] ⚠️ Task failure report rejected: lease expired or owned by another worker.", flush=True)
                    else:
                        worker_state['tasks_failed'] += 1
                    
                finally:
                    worker_state['status'] = 'idle'
                    worker_state['current_task_id'] = None
            else:
                # No task found
                pass
                
        except Exception as e:
            worker_state['last_action'] = f"Loop Exception: {str(e)[:20]}"
            print(f"[{WORKER_ID}] Loop Exception: {e}", flush=True)
            traceback.print_exc()
            time.sleep(2)

if __name__ == "__main__":
    print("WORKER MAIN STARTED", flush=True)
    worker_loop()