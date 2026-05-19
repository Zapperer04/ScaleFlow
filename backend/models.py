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
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

Base.metadata.create_all(engine)