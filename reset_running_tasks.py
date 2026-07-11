"""
Reset tasks that were spuriously set to 'running' by the broken poll endpoint
back to 'pending' so they can be properly claimed.
Also shows current pending/running state.
"""
import sys, os
sys.path.insert(0, 'backend')
os.environ['DB_MODE'] = 'sqlite'
from models import SessionLocal, Pipeline, Task
from datetime import datetime

db = SessionLocal()

try:
    # Find running tasks that have no active lease (expired or very short lease)
    running_tasks = db.query(Task).filter(Task.status == 'running').all()
    reset_count = 0
    for t in running_tasks:
        # Tasks spuriously claimed by the broken poll: they will have a recently-set lease
        # but no worker actually executing them. Reset to pending.
        print(f"  Running task {t.id} ({t.type}): worker={t.assigned_worker_id}, lease_expires={t.lease_expires_at}")
        # Reset to pending - the worker was never actually running them
        t.status = 'pending'
        t.assigned_worker_id = None
        t.lease_token = None
        t.lease_expires_at = None
        t.started_at = None
        reset_count += 1

    db.commit()
    print(f"\nReset {reset_count} spuriously-running tasks back to pending.")

    # Verify state
    pending = db.query(Task).filter(Task.status == 'pending').all()
    print(f"\nPending tasks ({len(pending)}):")
    for t in pending:
        print(f"  Task {t.id} ({t.type}) pipeline={t.pipeline_id} deps={t.dependencies}")

finally:
    db.close()
