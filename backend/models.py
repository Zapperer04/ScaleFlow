from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import json
import os

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

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/task_schedular")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Pipeline(Base):
    __tablename__ = 'pipelines'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    pipeline_type = Column(String(50), nullable=False)
    status = Column(String(20), default='created') # created, running, completed, failed, cancelled, blocked
    created_at = Column(DateTime, default=datetime.now)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'pipeline_type': self.pipeline_type,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message
        }

class Artifact(Base):
    __tablename__ = 'artifacts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    pipeline_id = Column(Integer, ForeignKey('pipelines.id'))
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=True)
    artifact_type = Column(String(50), nullable=False)
    storage_uri = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=True)
    checksum = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'pipeline_id': self.pipeline_id,
            'task_id': self.task_id,
            'artifact_type': self.artifact_type,
            'storage_uri': self.storage_uri,
            'metadata_json': json.loads(self.metadata_json) if self.metadata_json else None,
            'checksum': self.checksum,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class TaskDependency(Base):
    __tablename__ = 'task_dependencies'
    task_id = Column(Integer, ForeignKey('tasks.id'), primary_key=True)
    depends_on_id = Column(Integer, ForeignKey('tasks.id'), primary_key=True)

class TaskLog(Base):
    __tablename__ = 'task_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey('tasks.id'))
    event_type = Column(String(50), nullable=False)
    message = Column(Text, nullable=True)
    worker_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'event_type': self.event_type,
            'message': self.message,
            'worker_id': self.worker_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Task(Base):
    __tablename__ = 'tasks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(50), nullable=False)
    data = Column(Text, nullable=False)
    status = Column(String(20), default='pending')
    priority = Column(String(10), default='medium')  
    dependencies = Column(Text, nullable=True) # Legacy
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    assigned_worker_id = Column(String(100), nullable=True)
    lease_token = Column(String(100), nullable=True)
    lease_expires_at = Column(DateTime, nullable=True)
    recovered_count = Column(Integer, default=0)
    
    # Phase 2 columns
    pipeline_id = Column(Integer, ForeignKey('pipelines.id'), nullable=True)
    input_artifact_ids = Column(Text, nullable=True) # JSON list
    output_artifact_ids = Column(Text, nullable=True) # JSON list
    blocked_reason = Column(Text, nullable=True)
    
    dependent_on = relationship(
        'Task',
        secondary='task_dependencies',
        primaryjoin=id==TaskDependency.task_id,
        secondaryjoin=id==TaskDependency.depends_on_id,
        backref="required_by"
    )
    
    logs = relationship('TaskLog', backref='task', order_by='TaskLog.created_at')
    
    def to_dict(self):
        legacy_deps = json.loads(self.dependencies) if self.dependencies else []
        new_deps = [t.id for t in self.dependent_on] if hasattr(self, 'dependent_on') else []
        all_deps = list(set(legacy_deps + new_deps))
        
        try:
            input_ids = json.loads(self.input_artifact_ids) if self.input_artifact_ids else []
        except Exception:
            input_ids = []
            
        try:
            output_ids = json.loads(self.output_artifact_ids) if self.output_artifact_ids else []
        except Exception:
            output_ids = []
            
        return {
            'id': self.id,
            'type': self.type,
            'data': json.loads(self.data),
            'status': self.status,
            'priority': self.priority,
            'dependencies': all_deps,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'assigned_worker_id': self.assigned_worker_id,
            'lease_token': self.lease_token,
            'lease_expires_at': self.lease_expires_at.isoformat() if self.lease_expires_at else None,
            'recovered_count': self.recovered_count,
            'pipeline_id': self.pipeline_id,
            'input_artifact_ids': input_ids,
            'output_artifact_ids': output_ids,
            'blocked_reason': self.blocked_reason
        }

class FileRecord(Base):
    __tablename__ = 'file_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    storage_uri = Column(Text, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    status = Column(String(20), default='uploaded') # uploaded, processing, processed, failed
    pipeline_id = Column(Integer, ForeignKey('pipelines.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    error_message = Column(Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'original_filename': self.original_filename,
            'file_type': self.file_type,
            'storage_uri': self.storage_uri,
            'size_bytes': self.size_bytes,
            'status': self.status,
            'pipeline_id': self.pipeline_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'error_message': self.error_message
        }

Base.metadata.create_all(engine)

# Auto-migration for existing tables
from sqlalchemy import text
with engine.begin() as conn:
    conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS assigned_worker_id VARCHAR(100);"))
    conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS lease_token VARCHAR(100);"))
    conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS lease_expires_at TIMESTAMP;"))
    conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS recovered_count INTEGER DEFAULT 0;"))
    conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS pipeline_id INTEGER;"))
    conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS input_artifact_ids TEXT;"))
    conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS output_artifact_ids TEXT;"))
    conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS blocked_reason TEXT;"))