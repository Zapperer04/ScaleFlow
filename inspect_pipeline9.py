import sys, os
sys.path.insert(0, 'backend')
os.environ['DB_MODE'] = 'sqlite'
from models import SessionLocal, Pipeline, Task
db = SessionLocal()
pipe = db.query(Pipeline).filter(Pipeline.id == 9).first()
print(f'Pipeline 9: status={pipe.status}')
tasks = db.query(Task).filter(Task.pipeline_id == 9).order_by(Task.id).all()
for t in tasks:
    print(f'  Task {t.id} ({t.type}): status={t.status}, deps={t.dependencies}, worker={t.assigned_worker_id}')
db.close()
