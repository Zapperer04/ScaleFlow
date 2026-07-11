import sys, os
sys.path.insert(0, 'backend')
os.environ['DB_MODE'] = 'sqlite'
from models import SessionLocal, Pipeline, Task
db = SessionLocal()

# Check task/pipeline #565 - could be task id or pipeline id
print("=== Task #565 ===")
t = db.query(Task).filter(Task.id == 565).first()
if t:
    print(f"Task 565: type={t.type}, status={t.status}, pipeline={t.pipeline_id}, worker={t.assigned_worker_id}, error={t.error_message}")
else:
    print("Task #565 not found")

print("\n=== Pipeline #565 ===")
p = db.query(Pipeline).filter(Pipeline.id == 565).first()
if p:
    print(f"Pipeline 565: status={p.status}, name={p.name}")
    tasks = db.query(Task).filter(Task.pipeline_id == 565).order_by(Task.id).all()
    for t in tasks:
        print(f"  Task {t.id} ({t.type}): {t.status}")
else:
    print("Pipeline #565 not found")

print("\n=== Overall System State ===")
from sqlalchemy import func
statuses = db.query(Task.status, func.count(Task.id)).group_by(Task.status).all()
for s, c in statuses:
    print(f"  Tasks {s}: {c}")

pipe_statuses = db.query(Pipeline.status, func.count(Pipeline.id)).group_by(Pipeline.status).all()
for s, c in pipe_statuses:
    print(f"  Pipelines {s}: {c}")

print("\n=== Recent Running Tasks ===")
running = db.query(Task).filter(Task.status == 'running').all()
for t in running:
    print(f"  Task {t.id} ({t.type}) pipeline={t.pipeline_id} worker={t.assigned_worker_id} lease_expires={t.lease_expires_at}")

db.close()
