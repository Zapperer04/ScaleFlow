from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import json
import redis
import os
from functools import wraps
from models import SessionLocal, Task, TaskDependency, TaskLog, load_env

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

@app.route('/tasks', methods=['POST'])
@require_api_key
def create_task():
    db = SessionLocal()
    try:
        data = request.json
        if not data or 'type' not in data:
            return jsonify({"error": "Missing 'type' field"}), 400
            
        priority = data.get('priority', 'medium')
        if priority not in ['high', 'medium', 'low']:
            return jsonify({'error': 'Priority must be high, medium, or low'}), 400
            
        dependencies = data.get('dependencies', [])
        
        # Verify dependencies exist
        for dep_id in dependencies:
            dep_task = db.query(Task).filter(Task.id == dep_id).first()
            if not dep_task:
                return jsonify({'error': f'Dependency task {dep_id} not found'}), 400

        task = Task(
            type=data.get('type'),
            data=json.dumps(data.get('data', {})),
            priority=priority,
            max_retries=data.get('max_retries', 3),
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

if __name__ == '__main__':
    port = int(os.environ.get("API_PORT", 5000))
    app.run(debug=True, port=port, host='0.0.0.0')