from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import json
import redis
import os
import uuid
import time
from functools import wraps
from models import SessionLocal, Task, TaskDependency, TaskLog, load_env
from task_registry import TASK_REGISTRY, validate_task_payload

load_env()

API_KEY = os.environ.get("API_KEY", "dev_secret_api_key")
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
TASK_RUNNING_TIMEOUT_SECONDS = int(os.environ.get("TASK_RUNNING_TIMEOUT_SECONDS", 300))

app = Flask(__name__)
if "*" in ALLOWED_ORIGINS:
    CORS(app)
else:
    CORS(app, resources={r"/*": {"origins": ALLOWED_ORIGINS}})

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

PRIORITY_QUEUES = {
    'high': 'task_queue_high',
    'medium': 'task_queue_medium',
    'low': 'task_queue_low'
}
WORKER_HEARTBEAT_EXPIRY = 30

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        provided_key = request.headers.get("X-API-Key")
        if not provided_key or provided_key != API_KEY:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function

def create_task_log(db, task_id, event_type, message, worker_id=None):
    log = TaskLog(
        task_id=task_id,
        event_type=event_type,
        message=message,
        worker_id=worker_id
    )
    db.add(log)
    return log

def reap_stuck_tasks(db):
    """Finds tasks stuck in 'running' state and marks them as failed"""
    timeout_threshold = datetime.now() - timedelta(seconds=TASK_RUNNING_TIMEOUT_SECONDS)
    stuck_tasks = db.query(Task).filter(Task.status == 'running', Task.started_at < timeout_threshold).all()
    for task in stuck_tasks:
        task.retry_count += 1
        task.error_message = "Task timed out after worker crash or no heartbeat"
        create_task_log(db, task.id, "task_timed_out", f"Timed out after {TASK_RUNNING_TIMEOUT_SECONDS}s")
        
        if task.retry_count < task.max_retries:
            task.status = 'pending'
            add_task_to_queue(task.id, task.priority, db=db)
            create_task_log(db, task.id, "task_retried", f"Auto-retrying (Attempt {task.retry_count})")
        else:
            task.status = 'failed'
            create_task_log(db, task.id, "task_failed", "Max retries reached after timeout")
    if stuck_tasks:
        db.commit()

def check_dependencies_met(task_id, db):
    """Check if all dependencies for a task are completed"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return True
    
    waiting = False
    
    # Check old json dependencies
    if task.dependencies and task.dependencies != "[]":
        try:
            legacy_deps = json.loads(task.dependencies)
            for dep_id in legacy_deps:
                dep_task = db.query(Task).filter(Task.id == dep_id).first()
                if not dep_task or dep_task.status != 'completed':
                    waiting = True
        except:
            pass

    # Check new relational dependencies
    if hasattr(task, 'dependent_on'):
        for dep_task in task.dependent_on:
            if dep_task.status != 'completed':
                waiting = True
                
    if waiting:
        return False
        
    return True

def add_task_to_queue(task_id, priority='medium', db=None):
    queue_name = PRIORITY_QUEUES.get(priority, 'task_queue_medium')
    redis_client.lpush(queue_name, task_id)
    if db:
        create_task_log(db, task_id, "task_queued", f"Pushed to {priority} priority queue")

@app.route('/task-types', methods=['GET'])
def get_task_types():
    task_types_list = []
    for type_key, details in TASK_REGISTRY.items():
        type_data = details.copy()
        type_data['type'] = type_key
        task_types_list.append(type_data)
    return jsonify(task_types_list), 200

@app.route('/tasks', methods=['POST'])
@require_api_key
def create_task():
    db = SessionLocal()
    try:
        data = request.json
        if not data or 'type' not in data:
            return jsonify({"error": "Missing 'type' field"}), 400
            
        task_type = data.get('type')
        task_data = data.get('data', {})
        
        # Validate task payload against the registry schema
        is_valid, err_msg = validate_task_payload(task_type, task_data)
        if not is_valid:
            return jsonify({"error": err_msg}), 400
            
        priority = data.get('priority', 'medium')
        if priority not in ['high', 'medium', 'low']:
            return jsonify({'error': 'Priority must be high, medium, or low'}), 400
            
        dependencies = data.get('dependencies', [])
        
        # Verify dependencies exist
        for dep_id in dependencies:
            dep_task = db.query(Task).filter(Task.id == dep_id).first()
            if not dep_task:
                return jsonify({'error': f'Dependency task {dep_id} not found'}), 400

        # Retrieve retry policy default
        registry_info = TASK_REGISTRY.get(task_type, {})
        default_max_retries = registry_info.get("retry_policy", {}).get("max_retries", 3)
        max_retries = data.get('max_retries', default_max_retries)

        task = Task(
            type=task_type,
            data=json.dumps(task_data),
            priority=priority,
            max_retries=max_retries,
            status='pending',
            dependencies="[]" 
        )
        db.add(task)
        db.flush() 
        
        create_task_log(db, task.id, "task_created", f"Task created via API")
        
        # Insert relational dependencies
        for dep_id in dependencies:
            db.add(TaskDependency(task_id=task.id, depends_on_id=dep_id))
            
        if dependencies:
            create_task_log(db, task.id, "dependency_waiting", f"Waiting on {len(dependencies)} tasks")
            
        db.commit()
        db.refresh(task)
        
        if check_dependencies_met(task.id, db):
            add_task_to_queue(task.id, priority, db=db)
            db.commit()
        
        return jsonify(task.to_dict()), 201
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@app.route('/tasks', methods=['GET'])
def get_tasks():
    db = SessionLocal()
    try:
        reap_stuck_tasks(db)
        
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        status = request.args.get('status')
        priority = request.args.get('priority')
        
        query = db.query(Task)
        if status:
            query = query.filter(Task.status == status)
        if priority:
            query = query.filter(Task.priority == priority)
            
        total_tasks = query.count()
        tasks = query.order_by(Task.id.desc()).offset((page - 1) * limit).limit(limit).all()
        
        total_pages = (total_tasks + limit - 1) // limit if limit > 0 else 0
        
        # Fetch Redis queues
        high_queue = redis_client.lrange('task_queue_high', 0, -1) or []
        medium_queue = redis_client.lrange('task_queue_medium', 0, -1) or []
        low_queue = redis_client.lrange('task_queue_low', 0, -1) or []
        
        queues_map = {
            'high': high_queue,
            'medium': medium_queue,
            'low': low_queue
        }
        
        tasks_dicts = []
        for task in tasks:
            td = task.to_dict()
            if task.status == 'pending':
                in_redis = False
                q_name = None
                q_pos = None
                
                p_queue_name = PRIORITY_QUEUES.get(task.priority, 'task_queue_medium')
                p_list = redis_client.lrange(p_queue_name, 0, -1) or []
                
                task_id_str = str(task.id)
                if task_id_str in p_list:
                    in_redis = True
                    q_name = p_queue_name
                    try:
                        idx = p_list.index(task_id_str)
                        q_pos = len(p_list) - idx
                    except ValueError:
                        pass
                else:
                    for q_key, lst in queues_map.items():
                        if task_id_str in lst:
                            in_redis = True
                            q_name = PRIORITY_QUEUES.get(q_key)
                            try:
                                idx = lst.index(task_id_str)
                                q_pos = len(lst) - idx
                            except ValueError:
                                pass
                            break
                
                td['queued_in_redis'] = in_redis
                td['queue_name'] = q_name
                td['queue_position'] = q_pos
            else:
                td['queued_in_redis'] = False
                td['queue_name'] = None
                td['queue_position'] = None
            
            tasks_dicts.append(td)

        return jsonify({
            "tasks": tasks_dicts,
            "metadata": {
                "current_page": page,
                "limit": limit,
                "total_tasks": total_tasks,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@app.route('/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        return jsonify(task.to_dict())
    finally:
        db.close()

@app.route('/tasks/<int:task_id>/details', methods=['GET'])
def get_task_details(task_id):
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return jsonify({'error': 'Task not found'}), 404
            
        task_dict = task.to_dict()
        task_dict['logs'] = [log.to_dict() for log in task.logs]
        
        # Extract worker_id from the latest log if available
        last_worker_id = None
        for log in reversed(task.logs):
            if log.worker_id:
                last_worker_id = log.worker_id
                break
        task_dict['worker_id'] = last_worker_id

        # Attach Redis queue parameters
        in_redis = False
        q_name = None
        q_pos = None
        if task.status == 'pending':
            p_queue_name = PRIORITY_QUEUES.get(task.priority, 'task_queue_medium')
            p_list = redis_client.lrange(p_queue_name, 0, -1) or []
            task_id_str = str(task.id)
            if task_id_str in p_list:
                in_redis = True
                q_name = p_queue_name
                try:
                    idx = p_list.index(task_id_str)
                    q_pos = len(p_list) - idx
                except ValueError:
                    pass
            else:
                for q_key, queue_val in PRIORITY_QUEUES.items():
                    lst = redis_client.lrange(queue_val, 0, -1) or []
                    if task_id_str in lst:
                        in_redis = True
                        q_name = queue_val
                        try:
                            idx = lst.index(task_id_str)
                            q_pos = len(lst) - idx
                        except ValueError:
                            pass
                        break
                        
        task_dict['queued_in_redis'] = in_redis
        task_dict['queue_name'] = q_name
        task_dict['queue_position'] = q_pos
        
        return jsonify(task_dict)
    finally:
        db.close()

@app.route('/tasks/<int:task_id>/retry', methods=['POST'])
@require_api_key
def retry_task(task_id):
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return jsonify({'error': 'Task not found'}), 404
            
        if task.status not in ['failed', 'timed_out', 'cancelled', 'pending']:
            return jsonify({'error': f'Cannot retry task with status {task.status}'}), 400
            
        data = request.json or {}
        force = data.get('force', False)
        
        if task.status != 'pending' and task.retry_count >= task.max_retries and not force:
            return jsonify({'error': 'Max retries reached. Use force=true to override.'}), 400
            
        if task.status == 'pending':
            task.error_message = None
            create_task_log(db, task.id, "task_requeued", "Task manually requeued by user")
        else:
            task.status = 'pending'
            task.error_message = None
            create_task_log(db, task.id, "task_retried", "Task manually retried by user")
            
        add_task_to_queue(task.id, task.priority, db=db)
        
        db.commit()
        db.refresh(task)
        return jsonify(task.to_dict())
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@app.route('/tasks/<int:task_id>/cancel', methods=['POST'])
@require_api_key
def cancel_task(task_id):
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return jsonify({'error': 'Task not found'}), 404
            
        if task.status in ['completed', 'failed', 'cancelled']:
            return jsonify({'error': f'Task is already {task.status}'}), 400
            
        task.status = 'cancelled'
        create_task_log(db, task.id, "task_cancelled", "Task manually cancelled by user")
        
        db.commit()
        db.refresh(task)
        return jsonify(task.to_dict())
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@app.route('/tasks/<int:task_id>/claim', methods=['POST'])
@require_api_key
def claim_task(task_id):
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return jsonify({'error': 'Task not found'}), 404
            
        if task.status not in ['pending', 'retryable']:
            return jsonify({'error': f'Task cannot be claimed in status {task.status}'}), 400
            
        data = request.json or {}
        worker_id = data.get('worker_id')
        if not worker_id:
            return jsonify({'error': 'worker_id is required'}), 400
            
        lease_token = str(uuid.uuid4())
        task.status = 'running'
        task.assigned_worker_id = worker_id
        task.lease_token = lease_token
        task.lease_expires_at = datetime.now() + timedelta(seconds=30)
        task.started_at = datetime.now()
        
        create_task_log(db, task.id, "task_claimed", f"Worker claimed task", worker_id=worker_id)
        
        db.commit()
        db.refresh(task)
        
        # Return task payload, lease_token, lease_expires_at
        td = task.to_dict()
        return jsonify(td), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@app.route('/tasks/<int:task_id>', methods=['PATCH'])
@require_api_key
def update_task(task_id):
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        data = request.json
        worker_id = data.get('worker_id')
        lease_token = data.get('lease_token')
        
        # Stale update validation for running task completion/failure
        if data.get('status') in ['completed', 'failed']:
            if task.status != 'running' or not worker_id or not lease_token or task.assigned_worker_id != worker_id or task.lease_token != lease_token:
                # Log stale_worker_update_rejected
                create_task_log(
                    db, 
                    task.id, 
                    "stale_worker_update_rejected", 
                    f"Rejected status update to {data.get('status')} from worker {worker_id} with token {lease_token}", 
                    worker_id=worker_id
                )
                db.commit()
                return jsonify({'error': 'Stale worker update rejected'}), 409
        
        if 'status' in data:
            task.status = data['status']
            if data['status'] == 'running':
                task.started_at = datetime.now()
                create_task_log(db, task.id, "task_started", "Worker started execution", worker_id=worker_id)
            elif data['status'] == 'completed':
                task.completed_at = datetime.now()
                create_task_log(db, task.id, "task_completed", "Execution finished successfully", worker_id=worker_id)
                
                # Check explicit dependencies
                dependent_relations = db.query(TaskDependency).filter(TaskDependency.depends_on_id == task.id).all()
                dependent_task_ids = [rel.task_id for rel in dependent_relations]
                
                waiting_tasks = db.query(Task).filter(Task.status == 'pending').all()
                for waiting_task in waiting_tasks:
                    is_dependent = False
                    if waiting_task.id in dependent_task_ids:
                        is_dependent = True
                    elif waiting_task.dependencies and waiting_task.dependencies != "[]":
                        try:
                            legacy_deps = json.loads(waiting_task.dependencies)
                            if task.id in legacy_deps:
                                is_dependent = True
                        except:
                            pass
                            
                    if is_dependent and check_dependencies_met(waiting_task.id, db):
                        create_task_log(db, waiting_task.id, "dependency_resolved", f"Dependencies met (Task #{task.id} completed)")
                        add_task_to_queue(waiting_task.id, waiting_task.priority, db=db)
                        
            elif data['status'] == 'failed':
                task.retry_count += 1
                error_msg = data.get('error_message', 'Unknown error')
                task.error_message = error_msg
                
                create_task_log(db, task.id, "task_failed", f"Failed: {error_msg}", worker_id=worker_id)
                
                if task.retry_count < task.max_retries:
                    task.status = 'pending'
                    create_task_log(db, task.id, "task_retried", f"Auto-retrying (Attempt {task.retry_count})")
                    add_task_to_queue(task_id, task.priority, db=db)
                else:
                    create_task_log(db, task.id, "task_failed", "Max retries reached")
        
        db.commit()
        db.refresh(task)
        return jsonify(task.to_dict())
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@app.route('/queues/stats', methods=['GET'])
def get_queue_stats():
    stats = {}
    total = 0
    for name, queue_key in PRIORITY_QUEUES.items():
        count = redis_client.llen(queue_key)
        stats[name] = count
        total += count
    stats['total'] = total
    return jsonify(stats), 200

@app.route('/workers/heartbeat', methods=['POST'])
@require_api_key
def worker_heartbeat():
    data = request.json
    worker_id = data.get('worker_id')
    if not worker_id:
        return jsonify({'error': 'worker_id required'}), 400
    
    worker_key = f'worker:{worker_id}'
    worker_data = {
        'worker_id': worker_id,
        'last_seen': datetime.now().isoformat(),
        'status': data.get('status', 'idle'),
        'current_task_id': data.get('current_task_id', None),
        'tasks_completed': data.get('tasks_completed', 0),
        'tasks_failed': data.get('tasks_failed', 0),
        'last_action': data.get('last_action', 'None')
    }
    redis_client.setex(worker_key, WORKER_HEARTBEAT_EXPIRY, json.dumps(worker_data))
    return jsonify({'status': 'ok'}), 200

@app.route('/workers', methods=['GET'])
def get_workers():
    worker_keys = redis_client.keys('worker:*')
    workers = []
    for key in worker_keys:
        worker_data = redis_client.get(key)
        if worker_data:
            workers.append(json.loads(worker_data))
    return jsonify(workers), 200

def scan_and_recover_tasks(db):
    now = datetime.now()
    # Scan running tasks where lease_expires_at < now
    expired_tasks = db.query(Task).filter(
        Task.status == 'running',
        Task.lease_expires_at.isnot(None),
        Task.lease_expires_at < now
    ).all()
    
    for task in expired_tasks:
        task.recovered_count = (task.recovered_count or 0) + 1
        
        if task.retry_count < task.max_retries:
            task.status = 'pending'
            task.retry_count += 1
            task.assigned_worker_id = None
            task.lease_token = None
            task.lease_expires_at = None
            
            # Requeue task to correct Redis priority queue
            add_task_to_queue(task.id, task.priority, db=db)
            
            create_task_log(
                db, 
                task.id, 
                "task_recovered_after_lease_expiry", 
                f"Task lease expired. Requeued (Attempt {task.retry_count}/{task.max_retries})"
            )
        else:
            task.status = 'failed'
            task.assigned_worker_id = None
            task.lease_token = None
            task.lease_expires_at = None
            task.error_message = "Max retries exceeded after lease expiry"
            
            create_task_log(
                db, 
                task.id, 
                "max_retries_exceeded_after_lease_expiry", 
                "Max retries exceeded after lease expiry. Marked as failed."
            )
            
    if expired_tasks:
        db.commit()
    return len(expired_tasks)

def run_recovery_scanner():
    print("[Recovery Scanner] Started background thread.", flush=True)
    while True:
        try:
            time.sleep(10)
            db = SessionLocal()
            try:
                scan_and_recover_tasks(db)
            except Exception as e:
                db.rollback()
                print(f"[Recovery Scanner] Error during scan: {e}", flush=True)
            finally:
                db.close()
        except Exception as e:
            print(f"[Recovery Scanner] Error in loop: {e}", flush=True)

@app.route('/tasks/test-recovery', methods=['GET', 'POST'])
def test_recovery_flow():
    test_logs = []
    def log_test(msg):
        test_logs.append(msg)
        print(f"[Test Recovery Flow] {msg}", flush=True)

    log_test("Starting recovery flow integration test suite...")
    
    with app.test_client() as client:
        headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
        
        # Test A: Normal valid task completes.
        log_test("--- Test A: Normal valid task completes ---")
        task_payload = {
            "type": "send_email",
            "priority": "medium",
            "data": {
                "to": "test_normal@example.com",
                "subject": "Normal Task",
                "body": "This is a normal test task."
            }
        }
        res = client.post('/tasks', json=task_payload, headers=headers)
        if res.status_code != 201:
            return jsonify({"status": "failed", "step": "create_normal_task", "error": res.json}), 400
        
        task_id = res.json['id']
        log_test(f"Task #{task_id} created successfully.")
        
        # Verify it's in Redis
        queue_name = PRIORITY_QUEUES['medium']
        in_queue = redis_client.lrange(queue_name, 0, -1)
        if str(task_id) not in in_queue:
            return jsonify({"status": "failed", "step": "verify_redis_queue", "error": f"Task not in Redis queue {queue_name}"}), 400
        log_test(f"Verified Task #{task_id} is in Redis queue.")
        
        # Pop from Redis to isolate
        redis_client.lrem(queue_name, 0, str(task_id))
        log_test(f"Removed Task #{task_id} from Redis queue to isolate test.")
        
        # Worker 1 claims task
        res = client.post(f'/tasks/{task_id}/claim', json={"worker_id": "worker-normal-1"}, headers=headers)
        if res.status_code != 200:
            return jsonify({"status": "failed", "step": "claim_normal_task", "error": res.json}), 400
        
        lease_token = res.json['lease_token']
        log_test(f"Task #{task_id} claimed by worker-normal-1. Token: {lease_token}")
        
        # Worker 1 completes task
        res = client.patch(f'/tasks/{task_id}', json={
            "status": "completed",
            "worker_id": "worker-normal-1",
            "lease_token": lease_token
        }, headers=headers)
        if res.status_code != 200:
            return jsonify({"status": "failed", "step": "complete_normal_task", "error": res.json}), 400
        log_test(f"Task #{task_id} marked completed by worker-normal-1.")
        
        # Verify DB
        db = SessionLocal()
        try:
            db_task = db.query(Task).filter(Task.id == task_id).first()
            if db_task.status != "completed":
                return jsonify({"status": "failed", "step": "verify_normal_db", "error": f"Expected completed, got {db_task.status}"}), 400
            log_test(f"Verified Task #{task_id} DB status is 'completed'.")
        finally:
            db.close()
            
        # Test B, C, D: Lease Expiry, Recovery, Claim by another worker, Stale Reject
        log_test("--- Test B, C, D: Lease Expiry, Recovery, Claim, Stale Reject ---")
        task_payload_hang = {
            "type": "send_email",
            "priority": "medium",
            "data": {
                "to": "test_hang@example.com",
                "subject": "Hang Task",
                "body": "This is a hang simulation task.",
                "simulate_hang_seconds": 45
            }
        }
        res = client.post('/tasks', json=task_payload_hang, headers=headers)
        if res.status_code != 201:
            return jsonify({"status": "failed", "step": "create_hang_task", "error": res.json}), 400
        
        hang_task_id = res.json['id']
        log_test(f"Hang Task #{hang_task_id} created successfully.")
        
        in_queue = redis_client.lrange(queue_name, 0, -1)
        if str(hang_task_id) not in in_queue:
            return jsonify({"status": "failed", "step": "verify_hang_redis_queue", "error": "Hang task not in Redis"}), 400
        log_test("Verified Hang Task is in Redis queue.")
        
        # Pop from Redis to isolate
        redis_client.lrem(queue_name, 0, str(hang_task_id))
        log_test("Removed Hang Task from Redis queue to isolate test.")
        
        # Worker 1 claims task
        res = client.post(f'/tasks/{hang_task_id}/claim', json={"worker_id": "worker-hang-1"}, headers=headers)
        if res.status_code != 200:
            return jsonify({"status": "failed", "step": "claim_hang_task", "error": res.json}), 400
        
        hang_lease_token_1 = res.json['lease_token']
        log_test(f"Hang Task #{hang_task_id} claimed by worker-hang-1. Token: {hang_lease_token_1}")
        
        # Simulate lease expiry by modifying lease_expires_at in DB
        db = SessionLocal()
        try:
            db_task = db.query(Task).filter(Task.id == hang_task_id).first()
            db_task.lease_expires_at = datetime.now() - timedelta(seconds=10)
            db.commit()
            log_test("Manually expired lease of Hang Task in database.")
            
            # Trigger recovery scanner logic
            num_recovered = scan_and_recover_tasks(db)
            log_test(f"Ran recovery scanner logic. Recovered count: {num_recovered}")
            
            # Verify DB state
            db_task = db.query(Task).filter(Task.id == hang_task_id).first()
            if db_task.status != "pending" or db_task.retry_count != 1 or db_task.recovered_count != 1:
                return jsonify({
                    "status": "failed", 
                    "step": "verify_recovered_status", 
                    "error": f"Unexpected recovered state: status={db_task.status}, retry={db_task.retry_count}, recovered={db_task.recovered_count}"
                }), 400
            log_test("Verified task state is pending with recovered/retry count = 1.")
        finally:
            db.close()
            
        # Verify it has been requeued in Redis
        in_queue = redis_client.lrange(queue_name, 0, -1)
        if str(hang_task_id) not in in_queue:
            return jsonify({"status": "failed", "step": "verify_requeued_redis", "error": "Recovered task was not requeued"}), 400
        log_test("Verified recovered task was successfully requeued in Redis.")
        
        # Pop from Redis to isolate
        redis_client.lrem(queue_name, 0, str(hang_task_id))
        
        # Worker 2 claims the recovered task
        res = client.post(f'/tasks/{hang_task_id}/claim', json={"worker_id": "worker-hang-2"}, headers=headers)
        if res.status_code != 200:
            return jsonify({"status": "failed", "step": "claim_recovered_task", "error": res.json}), 400
        
        hang_lease_token_2 = res.json['lease_token']
        log_test(f"Recovered Task claimed by worker-hang-2. Token: {hang_lease_token_2}")
        
        # Worker 1 (stale) tries to complete the task with its old token
        log_test("Worker 1 (stale) attempting completion...")
        res = client.patch(f'/tasks/{hang_task_id}', json={
            "status": "completed",
            "worker_id": "worker-hang-1",
            "lease_token": hang_lease_token_1
        }, headers=headers)
        
        if res.status_code != 409:
            return jsonify({"status": "failed", "step": "verify_stale_completion_rejected", "error": f"Expected status 409, got {res.status_code}"}), 400
        log_test("Stale completion attempt by worker-hang-1 successfully rejected with 409.")
        
        # Verify task log contains the stale_worker_update_rejected event
        db = SessionLocal()
        try:
            logs = db.query(TaskLog).filter(TaskLog.task_id == hang_task_id, TaskLog.event_type == "stale_worker_update_rejected").all()
            if not logs:
                return jsonify({"status": "failed", "step": "verify_stale_log", "error": "No 'stale_worker_update_rejected' log event"}), 400
            log_test("Verified 'stale_worker_update_rejected' log event recorded in DB.")
        finally:
            db.close()
            
        # Worker 2 completes the task
        res = client.patch(f'/tasks/{hang_task_id}', json={
            "status": "completed",
            "worker_id": "worker-hang-2",
            "lease_token": hang_lease_token_2
        }, headers=headers)
        if res.status_code != 200:
            return jsonify({"status": "failed", "step": "complete_recovered_task", "error": res.json}), 400
        log_test("Task completed successfully by worker-hang-2.")
        
        # Verify final status in DB
        db = SessionLocal()
        try:
            db_task = db.query(Task).filter(Task.id == hang_task_id).first()
            if db_task.status != "completed":
                return jsonify({"status": "failed", "step": "verify_hang_completed_db", "error": f"Expected completed, got {db_task.status}"}), 400
            log_test("Verified task final DB status is 'completed'.")
        finally:
            db.close()
            
        # Test E: Max retries exceeded
        log_test("--- Test E: Max retries exceeded ---")
        task_payload_fail = {
            "type": "send_email",
            "priority": "medium",
            "max_retries": 1,
            "data": {
                "to": "test_max_retry@example.com",
                "subject": "Max Retry Task",
                "body": "Should fail after max retries."
            }
        }
        res = client.post('/tasks', json=task_payload_fail, headers=headers)
        if res.status_code != 201:
            return jsonify({"status": "failed", "step": "create_max_retry_task", "error": res.json}), 400
        
        fail_task_id = res.json['id']
        log_test(f"Max retry task #{fail_task_id} created.")
        
        # Pop from Redis to isolate
        redis_client.lrem(queue_name, 0, str(fail_task_id))
        
        # Claim
        res = client.post(f'/tasks/{fail_task_id}/claim', json={"worker_id": "worker-fail-1"}, headers=headers)
        if res.status_code != 200:
            return jsonify({"status": "failed", "step": "claim_fail_task", "error": res.json}), 400
        log_test("Max retry task claimed by worker-fail-1.")
        
        # 1st Expiry -> recovery
        db = SessionLocal()
        try:
            db_task = db.query(Task).filter(Task.id == fail_task_id).first()
            db_task.lease_expires_at = datetime.now() - timedelta(seconds=10)
            db.commit()
            
            scan_and_recover_tasks(db)
            
            db_task = db.query(Task).filter(Task.id == fail_task_id).first()
            log_test(f"After 1st recovery: status={db_task.status}, retry_count={db_task.retry_count}")
            if db_task.status != "pending" or db_task.retry_count != 1:
                return jsonify({"status": "failed", "step": "first_fail_recovery", "error": f"Unexpected state: status={db_task.status}, retry={db_task.retry_count}"}), 400
        finally:
            db.close()
            
        # Pop from Redis to isolate
        redis_client.lrem(queue_name, 0, str(fail_task_id))
        
        # 2nd Claim
        res = client.post(f'/tasks/{fail_task_id}/claim', json={"worker_id": "worker-fail-2"}, headers=headers)
        if res.status_code != 200:
            return jsonify({"status": "failed", "step": "second_claim_fail_task", "error": res.json}), 400
            
        # 2nd Expiry -> recovery (max retries exceeded)
        db = SessionLocal()
        try:
            db_task = db.query(Task).filter(Task.id == fail_task_id).first()
            db_task.lease_expires_at = datetime.now() - timedelta(seconds=10)
            db.commit()
            
            scan_and_recover_tasks(db)
            
            db_task = db.query(Task).filter(Task.id == fail_task_id).first()
            log_test(f"After 2nd recovery: status={db_task.status}, retry_count={db_task.retry_count}")
            if db_task.status != "failed":
                return jsonify({"status": "failed", "step": "second_fail_recovery", "error": f"Expected status 'failed', got '{db_task.status}'"}), 400
            
            # Check log
            logs = db.query(TaskLog).filter(TaskLog.task_id == fail_task_id, TaskLog.event_type == "max_retries_exceeded_after_lease_expiry").all()
            if not logs:
                return jsonify({"status": "failed", "step": "verify_max_retry_log", "error": "No 'max_retries_exceeded_after_lease_expiry' event found"}), 400
            log_test("Verified task failed due to lease expiry exceeding max retries.")
        finally:
            db.close()
            
        log_test("All integration tests passed successfully.")
        return jsonify({
            "status": "success",
            "logs": test_logs
        }), 200

import threading
scanner_thread = threading.Thread(target=run_recovery_scanner, daemon=True)
scanner_thread.start()

if __name__ == '__main__':
    port = int(os.environ.get("API_PORT", 5000))
    app.run(debug=True, port=port, host='0.0.0.0')