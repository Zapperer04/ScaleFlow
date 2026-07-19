import os
import json
import hashlib

# Base storage path: storage/pipelines/{pipeline_id}/task_{task_id}_{artifact_type}.json
BASE_STORAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "storage"))

def calculate_checksum(data_str):
    return hashlib.sha256(data_str.encode('utf-8')).hexdigest()

def get_artifact_filepath(pipeline_id, task_id, artifact_type):
    filename = f"task_{task_id}_{artifact_type}.json"
    pipeline_dir = os.path.join(BASE_STORAGE_DIR, "pipelines", str(pipeline_id))
    return os.path.join(pipeline_dir, filename), f"storage/pipelines/{pipeline_id}/{filename}"

def save_artifact_to_disk(pipeline_id, task_id, artifact_type, data):
    """
    Saves JSON data to filesystem.
    data: dict, list, or string
    Returns: (storage_uri, checksum)
    """
    if isinstance(data, (dict, list)):
        data_str = json.dumps(data)
    else:
        data_str = str(data)
        
    checksum = calculate_checksum(data_str)
    file_path, storage_uri = get_artifact_filepath(pipeline_id, task_id, artifact_type)
    
    from backend.infrastructure.providers.bootstrap import get_container
    from backend.infrastructure.repositories.legacy_storage_adapter import LegacyStorageAdapter
    
    art_store = get_container().artifact_store
    data_bytes = LegacyStorageAdapter.to_bytes(data)
    art_store.save_artifact(storage_uri, data_bytes)
        
    return storage_uri, checksum

def load_artifact_from_disk(storage_uri):
    """
    Loads JSON data from filesystem using storage_uri.
    """
    from backend.infrastructure.providers.bootstrap import get_container
    from backend.infrastructure.repositories.legacy_storage_adapter import LegacyStorageAdapter
    
    art_store = get_container().artifact_store
    data_bytes = art_store.load_artifact(storage_uri)
    return LegacyStorageAdapter.from_bytes(data_bytes)

def save_artifact(db, pipeline_id, task_id, artifact_type, data, metadata=None):
    """
    Saves artifact data to disk and registers it in the DB.
    Only called by the backend since it requires db connection.
    """
    from backend.repositories.unit_of_work import UnitOfWork
    from backend.infrastructure.persistence.sqlalchemy.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork
    from backend.domain.entities.artifact import Artifact as DomainArtifact
    from backend.domain.value_objects.pipeline_id import PipelineId
    
    storage_uri, checksum = save_artifact_to_disk(pipeline_id, task_id, artifact_type, data)
    
    if isinstance(db, UnitOfWork):
        uow = db
    else:
        uow = SqlAlchemyUnitOfWork(db)
        
    metadata_json = json.dumps(metadata) if metadata else None
    domain_art = DomainArtifact(
        artifact_id=None,
        pipeline_id=PipelineId(pipeline_id),
        task_id=task_id,
        artifact_type=artifact_type,
        storage_uri=storage_uri,
        metadata_json=metadata_json,
        checksum=checksum
    )
    uow.artifacts.create(domain_art)
    if not isinstance(db, UnitOfWork):
        db.flush()
    return domain_art

def load_artifact(db, artifact_id):
    """
    Loads artifact DB record and its content from disk.
    Only called by the backend.
    """
    from backend.repositories.unit_of_work import UnitOfWork
    from backend.infrastructure.persistence.sqlalchemy.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork
    
    if isinstance(db, UnitOfWork):
        uow = db
    else:
        uow = SqlAlchemyUnitOfWork(db)
        
    artifact = uow.artifacts.get(artifact_id)
    if not artifact:
        raise ValueError(f"Artifact with ID {artifact_id} not found")
        
    data = load_artifact_from_disk(artifact.storage_uri)
    return artifact, data

