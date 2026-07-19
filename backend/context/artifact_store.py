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

def save_artifact_to_disk(pipeline_id, task_id, artifact_type, data, art_store=None):
    """
    Saves JSON data to filesystem via the provided ArtifactStore.
    data: dict, list, or string
    art_store: ArtifactStore instance (must be provided by caller)
    Returns: (storage_uri, checksum)
    """
    _file_path, storage_uri = get_artifact_filepath(pipeline_id, task_id, artifact_type)

    if art_store is None:
        raise ValueError(
            "art_store must be provided explicitly. "
            "Pass container.artifact_store from the caller."
        )

    # Compute checksum over the canonical byte representation
    data_bytes = art_store._to_bytes(data)
    checksum = hashlib.sha256(data_bytes).hexdigest()
    art_store.save_artifact(storage_uri, data_bytes)

    return storage_uri, checksum

def load_artifact_from_disk(storage_uri, art_store=None):
    """
    Loads JSON data from filesystem using storage_uri.
    art_store: ArtifactStore instance (must be provided by caller)
    """
    if art_store is None:
        raise ValueError(
            "art_store must be provided explicitly. "
            "Pass container.artifact_store from the caller."
        )

    data_bytes = art_store.load_artifact(storage_uri)
    return art_store._from_bytes(data_bytes)

def save_artifact(db, pipeline_id, task_id, artifact_type, data, metadata=None, art_store=None):
    """
    Saves artifact data to disk and registers it in the DB.
    Only called by the backend since it requires db connection.
    art_store: ArtifactStore instance (must be provided by caller)
    """
    from backend.repositories.unit_of_work import UnitOfWork
    from backend.infrastructure.persistence.sqlalchemy.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork
    from backend.domain.entities.artifact import Artifact as DomainArtifact
    from backend.domain.value_objects.pipeline_id import PipelineId

    storage_uri, checksum = save_artifact_to_disk(pipeline_id, task_id, artifact_type, data, art_store=art_store)

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

def load_artifact(db, artifact_id, art_store=None):
    """
    Loads artifact DB record and its content from disk.
    Only called by the backend.
    art_store: ArtifactStore instance (must be provided by caller)
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

    data = load_artifact_from_disk(artifact.storage_uri, art_store=art_store)
    return artifact, data
