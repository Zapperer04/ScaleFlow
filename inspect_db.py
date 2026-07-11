import sys, os
sys.path.insert(0, 'backend')
os.environ['DB_MODE'] = 'sqlite'
from models import SessionLocal, Pipeline, Task
db = SessionLocal()

# Check last 5 pipelines
pipes = db.query(Pipeline).order_by(Pipeline.id.desc()).limit(5).all()
for pipe in pipes:
    print(f'Pipeline {pipe.id}: status={pipe.status}, name={pipe.name}')
    tasks = db.query(Task).filter(Task.pipeline_id == pipe.id).all()
    for t in tasks:
        print(f'  Task {t.id} ({t.type}): status={t.status}, deps={t.dependencies}')

# Also check if there are any pending tasks overall
pending = db.query(Task).filter(Task.status == 'pending').all()
print(f'\nTotal pending tasks: {len(pending)}')
for t in pending:
    print(f'  Task {t.id} ({t.type}) pipeline={t.pipeline_id}')

db.close()
