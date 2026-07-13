# database.py — ScaleFlow database models with production hardening

import base64
import gzip
import json
import logging
import os
import sys
import time
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    Text,
    ForeignKey,
    Boolean,
    Enum,
    JSON,
    Index,
    UniqueConstraint,
    event,
    inspect,
    text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.types import TypeDecorator

# ------------------------------------------------------------------------------
# Environment & DB config
# ------------------------------------------------------------------------------
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

logger = logging.getLogger(__name__)

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
ACTIVE_DB_MODE = DB_MODE

# Determine JSON type per dialect (PostgreSQL: JSONB, SQLite: JSON)
def _get_json_type():
    if DATABASE_URL.startswith("sqlite"):
        return JSON
    # PostgreSQL: use JSONB for better indexing
    try:
        from sqlalchemy.dialects.postgresql import JSONB
        return JSONB
    except ImportError:
        return JSON

JSON_TYPE = _get_json_type()

# Connection pool config
POOL_SIZE = 15
MAX_OVERFLOW = 25
POOL_RECYCLE = 300
POOL_TIMEOUT = 30
POOL_USE_LIFO = True

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        pool_size=POOL_SIZE,
        max_overflow=MAX_OVERFLOW,
        pool_recycle=POOL_RECYCLE,
        pool_timeout=POOL_TIMEOUT,
        pool_use_lifo=POOL_USE_LIFO,
        pool_pre_ping=True,
    )
    # Enable WAL journal mode and high busy_timeout
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=15000")
        cursor.close()
else:
    engine = create_engine(
        DATABASE_URL,
        pool_size=POOL_SIZE,
        max_overflow=MAX_OVERFLOW,
        pool_recycle=POOL_RECYCLE,
        pool_timeout=POOL_TIMEOUT,
        pool_use_lifo=POOL_USE_LIFO,
        pool_pre_ping=True,
    )

Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)

# ------------------------------------------------------------------------------
# Custom Type: GzippedBinary (for snapshots)
# ------------------------------------------------------------------------------
class GzippedBinary(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            value = value.encode("utf-8")
        return base64.b64encode(value).decode("utf-8")

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            if isinstance(value, bytes):
                value = value.decode("utf-8")
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

# ------------------------------------------------------------------------------
# Enum definitions
# ------------------------------------------------------------------------------
class PipelineStatus(PyEnum):
    created = "created"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"
    blocked = "blocked"

class TaskStatus(PyEnum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"
    blocked = "blocked"
    deferred = "deferred"

class TaskPriority(PyEnum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"

class ArtifactType(PyEnum):
    document = "document"
    graph = "graph"
    chunk = "chunk"
    embedding = "embedding"
    bm25 = "bm25"
    report = "report"

class EventCategory(PyEnum):
    critical = "critical"
    operational = "operational"
    telemetry = "telemetry"
    debug = "debug"
    transient = "transient"

class FileStatus(PyEnum):
    uploaded = "uploaded"
    processing = "processing"
    processed = "processed"
    failed = "failed"

class WorkerStatus(PyEnum):
    active = "active"
    draining = "draining"
    offline = "offline"

# ------------------------------------------------------------------------------
# Mixins
# ------------------------------------------------------------------------------
class TimestampMixin:
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class VersionMixin:
    version = Column(Integer, default=0, nullable=False)

# ------------------------------------------------------------------------------
# Models
# ------------------------------------------------------------------------------
class Pipeline(Base, TimestampMixin, VersionMixin):
    __tablename__ = 'pipelines'
    __table_args__ = (
        Index('idx_pipelines_status', 'status'),
        Index('idx_pipelines_owner_instance_id', 'owner_instance_id'),
        Index('idx_pipelines_created_at', 'created_at'),
    )
    __mapper_args__ = {
        "version_id_col": "version"  # string name is supported and reliable
    }

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    pipeline_type = Column(String(50), nullable=False)
    status = Column(Enum(PipelineStatus), default=PipelineStatus.created, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    owner_instance_id = Column(String(100), nullable=True)
    owner_lease_expires_at = Column(DateTime, nullable=True)
    ownership_version = Column(Integer, default=0)
    is_critical = Column(Boolean, default=False)

    # Relationships
    tasks = relationship('Task', backref='pipeline', cascade='all, delete-orphan')
    artifacts = relationship('Artifact', backref='pipeline', cascade='all, delete-orphan')
    events = relationship('OrchestrationEvent', backref='pipeline', cascade='all, delete-orphan')
    snapshots = relationship('OrchestrationSnapshot', backref='pipeline', cascade='all, delete-orphan')
    files = relationship('FileRecord', backref='pipeline', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'pipeline_type': self.pipeline_type,
            'status': self.status.value if self.status else None,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None,
            'started_at': self.started_at.isoformat() + 'Z' if self.started_at else None,
            'completed_at': self.completed_at.isoformat() + 'Z' if self.completed_at else None,
            'error_message': self.error_message,
            'owner_instance_id': self.owner_instance_id,
            'owner_lease_expires_at': self.owner_lease_expires_at.isoformat() + 'Z' if self.owner_lease_expires_at else None,
            'ownership_version': self.ownership_version,
            'is_critical': self.is_critical,
            'version': self.version,
        }

class Task(Base, TimestampMixin, VersionMixin):
    __tablename__ = 'tasks'
    __table_args__ = (
        Index('idx_tasks_status', 'status'),
        Index('idx_tasks_priority', 'priority'),
        Index('idx_tasks_status_priority', 'status', 'priority'),
        Index('idx_tasks_lease_expires_at', 'lease_expires_at'),
        Index('idx_tasks_assigned_worker_id', 'assigned_worker_id'),
        Index('idx_tasks_pipeline_id', 'pipeline_id'),
        Index('idx_tasks_created_at', 'created_at'),
    )
    __mapper_args__ = {
        "version_id_col": "version"  # string name is supported and reliable
    }

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(50), nullable=False)
    data = Column(Text, nullable=False)  # Large JSON, kept as Text for compatibility
    status = Column(Enum(TaskStatus), default=TaskStatus.pending, nullable=False)
    priority = Column(Enum(TaskPriority), default=TaskPriority.medium, nullable=False)
    dependencies = Column(Text, nullable=True)  # Legacy JSON list
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    assigned_worker_id = Column(String(100), nullable=True)
    lease_token = Column(String(100), nullable=True)
    lease_expires_at = Column(DateTime, nullable=True)
    recovered_count = Column(Integer, default=0)
    lease_renewal_count = Column(Integer, default=0)

    last_progress_at = Column(DateTime, nullable=True)
    progress_json = Column(JSON_TYPE, nullable=True)  # JSONB on Postgres, JSON on SQLite

    pipeline_id = Column(Integer, ForeignKey('pipelines.id', ondelete='CASCADE'), nullable=True, index=True)
    input_artifact_ids = Column(Text, nullable=True)  # JSON list (keeping Text for backward compatibility)
    output_artifact_ids = Column(Text, nullable=True) # JSON list
    blocked_reason = Column(Text, nullable=True)
    deferred_at = Column(DateTime, nullable=True)

    # Relationships
    dependent_on = relationship(
        'Task',
        secondary='task_dependencies',
        primaryjoin=id==TaskDependency.task_id,
        secondaryjoin=id==TaskDependency.depends_on_id,
        backref="required_by",
        # No cascade; let the association table manage dependencies explicitly
    )
    logs = relationship('TaskLog', backref='task', cascade='all, delete-orphan')
    artifacts = relationship('Artifact', backref='task', cascade='all, delete-orphan')

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
            'status': self.status.value if self.status else None,
            'priority': self.priority.value if self.priority else None,
            'dependencies': all_deps,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None,
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
            'progress_json': self.progress_json,
            'version': self.version,
        }

class Artifact(Base, TimestampMixin):
    __tablename__ = 'artifacts'
    __table_args__ = (
        Index('idx_artifacts_pipeline_id', 'pipeline_id'),
        Index('idx_artifacts_task_id', 'task_id'),
        Index('idx_artifacts_artifact_type', 'artifact_type'),
        Index('idx_artifacts_created_at', 'created_at'),
        UniqueConstraint('checksum', name='uq_artifacts_checksum'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    pipeline_id = Column(Integer, ForeignKey('pipelines.id', ondelete='CASCADE'), index=True)
    task_id = Column(Integer, ForeignKey('tasks.id', ondelete='CASCADE'), nullable=True, index=True)
    artifact_type = Column(Enum(ArtifactType), nullable=False)
    storage_uri = Column(Text, nullable=False)
    metadata_json = Column(JSON_TYPE, nullable=True)  # JSONB / JSON
    checksum = Column(String(64), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'pipeline_id': self.pipeline_id,
            'task_id': self.task_id,
            'artifact_type': self.artifact_type.value if self.artifact_type else None,
            'storage_uri': self.storage_uri,
            'metadata_json': self.metadata_json,
            'checksum': self.checksum,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None,
        }

class TaskDependency(Base):
    __tablename__ = 'task_dependencies'
    __table_args__ = (
        Index('idx_task_deps_task_id', 'task_id'),
        Index('idx_task_deps_depends_on_id', 'depends_on_id'),
    )
    task_id = Column(Integer, ForeignKey('tasks.id', ondelete='CASCADE'), primary_key=True)
    depends_on_id = Column(Integer, ForeignKey('tasks.id', ondelete='CASCADE'), primary_key=True)

class TaskLog(Base, TimestampMixin):
    __tablename__ = 'task_logs'
    __table_args__ = (
        Index('idx_task_logs_task_id', 'task_id'),
        Index('idx_task_logs_event_type', 'event_type'),
        Index('idx_task_logs_created_at', 'created_at'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey('tasks.id', ondelete='CASCADE'), index=True)
    event_type = Column(String(50), nullable=False)
    message = Column(Text, nullable=True)
    worker_id = Column(String(100), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'event_type': self.event_type,
            'message': self.message,
            'worker_id': self.worker_id,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None,
        }

class FileRecord(Base, TimestampMixin):
    __tablename__ = 'file_records'
    __table_args__ = (
        Index('idx_file_records_pipeline_id', 'pipeline_id'),
        Index('idx_file_records_status', 'status'),
        Index('idx_file_records_created_at', 'created_at'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    storage_uri = Column(Text, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    status = Column(Enum(FileStatus), default=FileStatus.uploaded, nullable=False)
    pipeline_id = Column(Integer, ForeignKey('pipelines.id', ondelete='CASCADE'), nullable=True, index=True)
    error_message = Column(Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'original_filename': self.original_filename,
            'file_type': self.file_type,
            'storage_uri': self.storage_uri,
            'size_bytes': self.size_bytes,
            'status': self.status.value if self.status else None,
            'pipeline_id': self.pipeline_id,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None,
            'error_message': self.error_message,
        }

class OrchestrationEvent(Base, TimestampMixin):
    __tablename__ = 'orchestration_events'
    __table_args__ = (
        Index('idx_orchestration_events_pipeline_id', 'pipeline_id'),
        Index('idx_orchestration_events_task_id', 'task_id'),
        Index('idx_orchestration_events_event_type', 'event_type'),
        Index('idx_orchestration_events_event_category', 'event_category'),
        Index('idx_orchestration_events_created_at', 'created_at'),
        Index('idx_orchestration_events_correlation_id', 'correlation_id'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    pipeline_id = Column(Integer, ForeignKey('pipelines.id', ondelete='CASCADE'), nullable=True, index=True)
    task_id = Column(Integer, ForeignKey('tasks.id', ondelete='CASCADE'), nullable=True, index=True)
    event_type = Column(String(50), nullable=False)
    event_category = Column(Enum(EventCategory), nullable=False)
    message = Column(Text, nullable=True)
    worker_id = Column(String(100), nullable=True)
    lease_token = Column(String(100), nullable=True)
    correlation_id = Column(String(100), nullable=True)
    payload_json = Column(JSON_TYPE, nullable=False)  # JSONB / JSON
    segment_index = Column(Integer, default=0)
    event_version = Column(Integer, default=1)
    schema_version = Column(String(20), default="1.0")

    def to_dict(self):
        return {
            'id': self.id,
            'pipeline_id': self.pipeline_id,
            'task_id': self.task_id,
            'event_type': self.event_type,
            'event_category': self.event_category.value if self.event_category else None,
            'message': self.message,
            'worker_id': self.worker_id,
            'lease_token': self.lease_token,
            'correlation_id': self.correlation_id,
            'payload_json': self.payload_json,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None,
            'segment_index': self.segment_index,
            'event_version': self.event_version,
            'schema_version': self.schema_version,
        }

class OrchestrationSnapshot(Base, TimestampMixin):
    __tablename__ = 'orchestration_snapshots'
    __table_args__ = (
        Index('idx_orchestration_snapshots_pipeline_id', 'pipeline_id'),
        Index('idx_orchestration_snapshots_last_event_id', 'last_event_id'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    pipeline_id = Column(Integer, ForeignKey('pipelines.id', ondelete='CASCADE'), nullable=True, index=True)
    last_event_id = Column(Integer, nullable=False)
    snapshot_data = Column(GzippedBinary, nullable=False)  # gzip compressed JSON
    segment_index = Column(Integer, default=0)

    def to_dict(self):
        snapshot = {}
        try:
            if self.snapshot_data:
                data = self.snapshot_data
                if isinstance(data, str):
                    data = data.encode("utf-8")
                snapshot = json.loads(gzip.decompress(data).decode("utf-8"))
        except Exception:
            snapshot = {"__error__": "snapshot_decode_failed"}
        return {
            "id": self.id,
            "pipeline_id": self.pipeline_id,
            "last_event_id": self.last_event_id,
            "snapshot_data": snapshot,
            "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
            "updated_at": self.updated_at.isoformat() + "Z" if self.updated_at else None,
            "segment_index": self.segment_index,
        }

class OrchestratorInstance(Base, TimestampMixin):
    __tablename__ = 'orchestrator_instances'
    __table_args__ = (
        Index('idx_orchestrator_instances_is_leader', 'is_leader'),
        Index('idx_orchestrator_instances_last_heartbeat', 'last_heartbeat'),
        Index('idx_orchestrator_instances_status', 'status'),
    )

    instance_id = Column(String(100), primary_key=True)
    is_leader = Column(Boolean, default=False)
    last_heartbeat = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String(20), default='active')  # active, draining, offline

    def to_dict(self):
        return {
            'instance_id': self.instance_id,
            'is_leader': self.is_leader,
            'last_heartbeat': self.last_heartbeat.isoformat() + 'Z' if self.last_heartbeat else None,
            'status': self.status,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None,
        }

class WorkerRegistry(Base, TimestampMixin):
    __tablename__ = 'worker_registry'
    __table_args__ = (
        Index('idx_worker_registry_status', 'status'),
        Index('idx_worker_registry_last_seen', 'last_seen'),
    )

    worker_id = Column(String(100), primary_key=True)
    capabilities = Column(Text, nullable=False)  # JSON array
    resource_limits = Column(Text, nullable=True)  # JSON object
    last_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String(20), default='active')  # active, draining, offline

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
            'status': self.status,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None,
        }

# ------------------------------------------------------------------------------
# Initialization and auto‑migration
# ------------------------------------------------------------------------------
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

    # Add columns if missing (this is for backward compatibility)
    # For production, use Alembic migrations to handle schema evolutions properly.
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
        ("tasks", "progress_json", "TEXT"),  # Will remain TEXT in existing DBs
        ("tasks", "version", "INTEGER DEFAULT 0"),
        ("pipelines", "owner_instance_id", "VARCHAR(100)"),
        ("pipelines", "owner_lease_expires_at", "TIMESTAMP"),
        ("pipelines", "ownership_version", "INTEGER DEFAULT 0"),
        ("pipelines", "is_critical", "BOOLEAN DEFAULT FALSE"),
        ("pipelines", "version", "INTEGER DEFAULT 0"),
        ("orchestration_events", "segment_index", "INTEGER DEFAULT 0"),
        ("orchestration_events", "event_version", "INTEGER DEFAULT 1"),
        ("orchestration_events", "schema_version", "VARCHAR(20) DEFAULT '1.0'"),
        ("orchestration_snapshots", "segment_index", "INTEGER DEFAULT 0"),
    ]:
        if col not in existing_columns.get(table, []):
            try:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {ctype}"))
            except Exception:
                pass

    # Add missing indexes
    for idx_name, table, cols in [
        ("idx_tasks_status", "tasks", "status"),
        ("idx_tasks_priority", "tasks", "priority"),
        ("idx_tasks_status_priority", "tasks", ("status", "priority")),
        ("idx_tasks_lease", "tasks", "lease_expires_at"),
        ("idx_tasks_worker", "tasks", "assigned_worker_id"),
        ("idx_pipelines_status", "pipelines", "status"),
        ("idx_pipelines_owner", "pipelines", "owner_instance_id"),
        ("idx_orchestration_events_category", "orchestration_events", "event_category"),
        ("idx_orchestration_events_correlation", "orchestration_events", "correlation_id"),
        ("idx_artifacts_type", "artifacts", "artifact_type"),
        ("idx_file_records_status", "file_records", "status"),
    ]:
        try:
            with engine.begin() as conn:
                if isinstance(cols, tuple):
                    cols_str = ", ".join(cols)
                else:
                    cols_str = cols
                conn.execute(text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({cols_str})"))
        except Exception:
            try:
                with engine.begin() as conn:
                    conn.execute(text(f"CREATE INDEX {idx_name} ON {table} ({cols})"))
            except Exception:
                pass

    logger.info("Database initialization complete. For schema upgrades, please use Alembic migrations.")

# ------------------------------------------------------------------------------
# Module exports
# ------------------------------------------------------------------------------
__all__ = [
    "Base",
    "engine",
    "SessionLocal",
    "init_db",
    "Pipeline",
    "Task",
    "TaskDependency",
    "TaskLog",
    "Artifact",
    "FileRecord",
    "OrchestrationEvent",
    "OrchestrationSnapshot",
    "OrchestratorInstance",
    "WorkerRegistry",
    "PipelineStatus",
    "TaskStatus",
    "TaskPriority",
    "ArtifactType",
    "EventCategory",
    "FileStatus",
    "WorkerStatus",
]