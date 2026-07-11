from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey, Boolean, LargeBinary
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.types import TypeDecorator
from datetime import datetime
import gzip
import json
import logging
import os

def load_env():
    for path in ['.env', 'backend/.env', '../backend/.env']:
        try:
            with open(path) as f:
                for line in f:
                    if line.strip() and not line.startswith('#'):
                        key, val = line.strip().split('=', 1)
                        key_strip = key.strip()
                        if key_strip not in os.environ:
                            os.environ[key_strip] = val.strip()
                break
        except FileNotFoundError:
            pass

load_env()

import sys
import time

DB_MODE = os.environ.get("DB_MODE", "postgres").lower()
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/task_schedular")

def validate_postgres_connection(db_url, timeout=3, retries=5, backoff=1.5):
    last_err = None
    for attempt in range(retries):
        try:
            temp_engine = create_engine(db_url, connect_args={"connect_timeout": timeout})
            with temp_engine.connect() as conn:
                return True
        except Exception as e:
            last_err = e
            if attempt < retries - 1:
                sleep_time = backoff ** attempt
                print(f"DATABASE CONNECTION PENDING: Attempt {attempt+1}/{retries} failed to connect to PostgreSQL. Retrying in {sleep_time:.2f}s... Error: {e}", file=sys.stderr)
                time.sleep(sleep_time)
    raise last_err

if DB_MODE == "sqlite":
    DATABASE_URL = "sqlite:///task_schedular.db"
elif DB_MODE == "postgres":
    try:
        validate_postgres_connection(DATABASE_URL, timeout=3, retries=5, backoff=1.5)
    except Exception as e:
        print(f"DATABASE STARTUP ERROR: Failed to connect to PostgreSQL in postgres mode after retries. URL: {DATABASE_URL}", file=sys.stderr)
        raise e
elif DB_MODE == "auto":
    try:
        validate_postgres_connection(DATABASE_URL, timeout=2, retries=3, backoff=1.2)
    except Exception as e:
        print(f"DATABASE WARNING: PostgreSQL connection failed after retries. Falling back to SQLite task_schedular.db. Error: {e}", file=sys.stderr)
        DATABASE_URL = "sqlite:///task_schedular.db"
else:
    print(f"DATABASE WARNING: Invalid DB_MODE '{DB_MODE}'. Defaulting to postgres.", file=sys.stderr)
    try:
        validate_postgres_connection(DATABASE_URL, timeout=3, retries=5, backoff=1.5)
    except Exception as e:
        print(f"DATABASE STARTUP ERROR: Default postgres mode failed. URL: {DATABASE_URL}", file=sys.stderr)
        raise e

ACTIVE_DATABASE_URL = DATABASE_URL
# Make sure SQLite URL has check_same_thread=False
ACTIVE_DB_MODE = DB_MODE

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    
    # Enable WAL journal mode and set high busy_timeout to resolve lock conflicts
    from sqlalchemy import event
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=15000")
        cursor.close()
else:
    engine = create_engine(
        DATABASE_URL,
        pool_size=15,
        max_overflow=25,
        pool_recycle=300,
        pool_pre_ping=True
    )

Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)
logger = logging.getLogger(__name__)

import base64

class GzippedBinary(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            value = value.encode("utf-8")
        # value is bytes (compressed). Base64 encode to safe text representation.
        return base64.b64encode(value).decode("utf-8")

    def process_result_value(self, value, dialect):
        if value is None:
            return None

        # Value can be base64 encoded string, raw string, or bytes
        try:
            if isinstance(value, bytes):
                value = value.decode("utf-8")
            # Try decoding base64
            return base64.b64decode(value.encode("utf-8"))
        except Exception:
            logger.debug(
                "[SNAPSHOT] Legacy snapshot format detected (type=%s)",
                type(value).__name__,
            )
            if isinstance(value, bytes):
                return value
            if isinstance(value, memoryview):
                return value.tobytes()
            if isinstance(value, str):
                return value.encode("utf-8")
            return bytes(value)

class Pipeline(Base):
    __tablename__ = 'pipelines'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    pipeline_type = Column(String(50), nullable=False)
    status = Column(String(20), default='created') # created, running, completed, failed, cancelled, blocked
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Phase 8 Active/Active locks & fencing tokens
    owner_instance_id = Column(String(100), nullable=True)
    owner_lease_expires_at = Column(DateTime, nullable=True)
    ownership_version = Column(Integer, default=0)
    is_critical = Column(Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'pipeline_type': self.pipeline_type,
            'status': self.status,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'started_at': self.started_at.isoformat() + 'Z' if self.started_at else None,
            'completed_at': self.completed_at.isoformat() + 'Z' if self.completed_at else None,
            'error_message': self.error_message,
            'owner_instance_id': self.owner_instance_id,
            'owner_lease_expires_at': self.owner_lease_expires_at.isoformat() + 'Z' if self.owner_lease_expires_at else None,
            'ownership_version': self.ownership_version,
            'is_critical': self.is_critical
        }

class Artifact(Base):
    __tablename__ = 'artifacts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    pipeline_id = Column(Integer, ForeignKey('pipelines.id'), index=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=True, index=True)
    artifact_type = Column(String(50), nullable=False)
    storage_uri = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=True)
    checksum = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'pipeline_id': self.pipeline_id,
            'task_id': self.task_id,
            'artifact_type': self.artifact_type,
            'storage_uri': self.storage_uri,
            'metadata_json': json.loads(self.metadata_json) if self.metadata_json else None,
            'checksum': self.checksum,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None
        }

class TaskDependency(Base):
    __tablename__ = 'task_dependencies'
    task_id = Column(Integer, ForeignKey('tasks.id'), primary_key=True)
    depends_on_id = Column(Integer, ForeignKey('tasks.id'), primary_key=True)

class TaskLog(Base):
    __tablename__ = 'task_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), index=True)
    event_type = Column(String(50), nullable=False)
    message = Column(Text, nullable=True)
    worker_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'event_type': self.event_type,
            'message': self.message,
            'worker_id': self.worker_id,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None
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
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    assigned_worker_id = Column(String(100), nullable=True)
    lease_token = Column(String(100), nullable=True)
    lease_expires_at = Column(DateTime, nullable=True)
    recovered_count = Column(Integer, default=0)
    lease_renewal_count = Column(Integer, default=0)
    
    last_progress_at = Column(DateTime, nullable=True)
    progress_json = Column(Text, nullable=True)
    
    # Phase 2 columns
    pipeline_id = Column(Integer, ForeignKey('pipelines.id'), nullable=True, index=True)
    input_artifact_ids = Column(Text, nullable=True) # JSON list
    output_artifact_ids = Column(Text, nullable=True) # JSON list
    blocked_reason = Column(Text, nullable=True)
    deferred_at = Column(DateTime, nullable=True)
    
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
            
        # Compute queue wait duration and execution duration
        queue_wait = 0
        execution = 0
        if self.started_at and self.created_at:
            queue_wait = (self.started_at - self.created_at).total_seconds()
        elif self.created_at:
            queue_wait = (datetime.utcnow() - self.created_at).total_seconds()
            
        if self.completed_at and self.started_at:
            execution = (self.completed_at - self.started_at).total_seconds()
        elif self.started_at:
            execution = (datetime.utcnow() - self.started_at).total_seconds()

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
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'started_at': self.started_at.isoformat() + 'Z' if self.started_at else None,
            'completed_at': self.completed_at.isoformat() + 'Z' if self.completed_at else None,
            'assigned_worker_id': self.assigned_worker_id,
            'lease_token': self.lease_token,
            'lease_expires_at': self.lease_expires_at.isoformat() + 'Z' if self.lease_expires_at else None,
            'recovered_count': self.recovered_count,
            'lease_renewal_count': self.lease_renewal_count,
            'pipeline_id': self.pipeline_id,
            'input_artifact_ids': input_ids,
            'output_artifact_ids': output_ids,
            'blocked_reason': self.blocked_reason,
            'deferred_at': self.deferred_at.isoformat() + 'Z' if self.deferred_at else None,
            'queue_wait_duration': round(queue_wait, 2),
            'execution_duration': round(execution, 2),
            'last_progress_at': self.last_progress_at.isoformat() + 'Z' if self.last_progress_at else None,
            'progress_json': json.loads(self.progress_json) if self.progress_json else None
        }

class FileRecord(Base):
    __tablename__ = 'file_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    storage_uri = Column(Text, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    status = Column(String(20), default='uploaded') # uploaded, processing, processed, failed
    pipeline_id = Column(Integer, ForeignKey('pipelines.id'), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
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
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'error_message': self.error_message
        }

class OrchestrationEvent(Base):
    __tablename__ = 'orchestration_events'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    pipeline_id = Column(Integer, ForeignKey('pipelines.id'), nullable=True, index=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=True, index=True)
    event_type = Column(String(50), nullable=False)
    event_category = Column(String(20), nullable=False)  # critical, operational, telemetry, debug, transient
    message = Column(Text, nullable=True)
    worker_id = Column(String(100), nullable=True)
    lease_token = Column(String(100), nullable=True)
    correlation_id = Column(String(100), nullable=True)
    payload_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    segment_index = Column(Integer, default=0)
    # Event versioning for schema evolution
    event_version = Column(Integer, default=1)
    schema_version = Column(String(20), default="1.0")

    def to_dict(self):
        return {
            'id': self.id,
            'pipeline_id': self.pipeline_id,
            'task_id': self.task_id,
            'event_type': self.event_type,
            'event_category': self.event_category,
            'message': self.message,
            'worker_id': self.worker_id,
            'lease_token': self.lease_token,
            'correlation_id': self.correlation_id,
            'payload_json': json.loads(self.payload_json) if self.payload_json else {},
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'segment_index': self.segment_index,
            'event_version': self.event_version,
            'schema_version': self.schema_version
        }

class OrchestrationSnapshot(Base):
    __tablename__ = 'orchestration_snapshots'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    pipeline_id = Column(Integer, ForeignKey('pipelines.id'), nullable=True, index=True)
    last_event_id = Column(Integer, nullable=False)
    snapshot_data = Column(GzippedBinary, nullable=False)  # gzip compressed JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    segment_index = Column(Integer, default=0)

    def to_dict(self):
        snapshot = {}

        try:
            if self.snapshot_data:
                data = self.snapshot_data

                if isinstance(data, str):
                    data = data.encode("utf-8")

                snapshot = json.loads(
                    gzip.decompress(data).decode("utf-8")
                )
        except Exception:
            snapshot = {
                "__error__": "snapshot_decode_failed"
            }

        return {
            "id": self.id,
            "pipeline_id": self.pipeline_id,
            "last_event_id": self.last_event_id,
            "snapshot_data": snapshot,
            "created_at": self.created_at.isoformat() + "Z"
            if self.created_at else None,
            "segment_index": self.segment_index
        }

class OrchestratorInstance(Base):
    __tablename__ = 'orchestrator_instances'
    instance_id = Column(String(100), primary_key=True)
    is_leader = Column(Boolean, default=False)
    last_heartbeat = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default='active')

    def to_dict(self):
        return {
            'instance_id': self.instance_id,
            'is_leader': self.is_leader,
            'last_heartbeat': self.last_heartbeat.isoformat() + 'Z' if self.last_heartbeat else None,
            'status': self.status
        }

class WorkerRegistry(Base):
    __tablename__ = 'worker_registry'
    worker_id = Column(String(100), primary_key=True)
    capabilities = Column(Text, nullable=False)  # JSON array
    resource_limits = Column(Text, nullable=True)  # JSON object
    last_seen = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default='active')

    def to_dict(self):
        try:
            caps = json.loads(self.capabilities) if self.capabilities else []
        except:
            caps = []
        try:
            res_lim = json.loads(self.resource_limits) if self.resource_limits else {}
        except:
            res_lim = {}
        return {
            'worker_id': self.worker_id,
            'capabilities': caps,
            'resource_limits': res_lim,
            'last_seen': self.last_seen.isoformat() + 'Z' if self.last_seen else None,
            'status': self.status
        }

def init_db():
    Base.metadata.create_all(engine)

    # Auto-migration for existing tables (dialect-safe try/except blocks in separate transactions)
    from sqlalchemy import text, inspect

    try:
        inspector = inspect(engine)
        existing_columns = {}
        for table in ["tasks", "pipelines", "orchestration_events", "orchestration_snapshots"]:
            try:
                existing_columns[table] = [c["name"] for c in inspector.get_columns(table)]
            except Exception:
                existing_columns[table] = []
    except Exception:
        existing_columns = {}

    for table, col, ctype in [
        ("tasks", "assigned_worker_id", "VARCHAR(100)"),
        ("tasks", "lease_token", "VARCHAR(100)"),
        ("tasks", "lease_expires_at", "TIMESTAMP"),
        ("tasks", "recovered_count", "INTEGER DEFAULT 0"),
        ("tasks", "lease_renewal_count", "INTEGER DEFAULT 0"),
        ("tasks", "pipeline_id", "INTEGER"),
        ("tasks", "input_artifact_ids", "TEXT"),
        ("tasks", "output_artifact_ids", "TEXT"),
        ("tasks", "blocked_reason", "TEXT"),
        ("tasks", "deferred_at", "TIMESTAMP"),
        ("tasks", "last_progress_at", "TIMESTAMP"),
        ("tasks", "progress_json", "TEXT"),
        
        ("pipelines", "owner_instance_id", "VARCHAR(100)"),
        ("pipelines", "owner_lease_expires_at", "TIMESTAMP"),
        ("pipelines", "ownership_version", "INTEGER DEFAULT 0"),
        ("pipelines", "is_critical", "BOOLEAN DEFAULT FALSE"),
        
        ("orchestration_events", "segment_index", "INTEGER DEFAULT 0"),
        ("orchestration_events", "event_version", "INTEGER DEFAULT 1"),
        ("orchestration_events", "schema_version", "VARCHAR(20) DEFAULT '1.0'"),
        ("orchestration_snapshots", "segment_index", "INTEGER DEFAULT 0"),
        # Note: changing snapshot_data from TEXT to LargeBinary is a breaking change.
        # In a production migration, you'd need to handle conversion; here we assume a fresh DB or manual migration.
        # For SQLite, we need to alter table; for PostgreSQL we'd use ALTER COLUMN TYPE.
        # However, we rely on create_all for new DB, and for existing, we'll skip this ALTER as it's complex.
    ]:
        if col not in existing_columns.get(table, []):
            try:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {ctype}"))
            except Exception:
                pass

    # Auto-create indexes for foreign keys if missing
    for idx_name, table, col in [
        ("idx_artifacts_pipeline_id", "artifacts", "pipeline_id"),
        ("idx_artifacts_task_id", "artifacts", "task_id"),
        ("idx_task_logs_task_id", "task_logs", "task_id"),
        ("idx_tasks_pipeline_id", "tasks", "pipeline_id"),
        ("idx_file_records_pipeline_id", "file_records", "pipeline_id"),
        ("idx_orchestration_events_pipeline_id", "orchestration_events", "pipeline_id"),
        ("idx_orchestration_events_task_id", "orchestration_events", "task_id"),
        ("idx_orchestration_snapshots_pipeline_id", "orchestration_snapshots", "pipeline_id"),
    ]:
        try:
            with engine.begin() as conn:
                conn.execute(text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({col})"))
        except Exception:
            try:
                with engine.begin() as conn:
                    conn.execute(text(f"CREATE INDEX {idx_name} ON {table} ({col})"))
            except Exception:
                pass