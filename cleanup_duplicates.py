"""
Cleanup script: remove stale duplicate preprocess_document tasks where deps=None
(the ones created by the old buggy code that didn't check if template already had the node).
Only removes duplicates where the pipeline already has a valid preprocess_document with deps=[].
"""
import sys, os
sys.path.insert(0, 'backend')
os.environ['DB_MODE'] = 'sqlite'
from models import SessionLocal, Pipeline, Task, TaskDependency

db = SessionLocal()

try:
    pipelines = db.query(Pipeline).filter(
        Pipeline.status.in_(['running', 'created', 'recovering'])
    ).all()

    removed = 0
    for pipe in pipelines:
        tasks = db.query(Task).filter(Task.pipeline_id == pipe.id).all()
        preprocess_tasks = [t for t in tasks if t.type == 'preprocess_document']
        
        if len(preprocess_tasks) <= 1:
            continue
        
        # Find the one with deps=None (the bad one - created extra)
        # Keep the one with deps="[]" or deps=None that has TaskDependency entries for its children
        null_dep = [t for t in preprocess_tasks if t.dependencies is None]
        empty_dep = [t for t in preprocess_tasks if t.dependencies == '[]']
        
        if null_dep and empty_dep:
            # Remove the null_dep one (it has no children depending on it typically)
            for bad_task in null_dep:
                # Check if any other task depends on it via TaskDependency
                child_count = db.query(TaskDependency).filter(
                    TaskDependency.depends_on_id == bad_task.id
                ).count()
                if child_count == 0:
                    print(f"Removing orphan duplicate preprocess_document task {bad_task.id} from pipeline {pipe.id}")
                    db.delete(bad_task)
                    removed += 1
                else:
                    print(f"Task {bad_task.id} has {child_count} child dependencies - keeping")
    
    db.commit()
    print(f"\nDone. Removed {removed} duplicate orphan tasks.")

    # Verify
    pending = db.query(Task).filter(Task.status == 'pending').all()
    print(f"Remaining pending tasks: {len(pending)}")
    for t in pending:
        print(f"  Task {t.id} ({t.type}) pipeline={t.pipeline_id} deps={t.dependencies}")

finally:
    db.close()
