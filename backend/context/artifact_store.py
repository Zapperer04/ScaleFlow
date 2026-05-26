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
    
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(data_str)
        
    return storage_uri, checksum

def load_artifact_from_disk(storage_uri):
    """
    Loads JSON data from filesystem using storage_uri.
    """
    # The storage_uri is relative to the backend directory, e.g. storage/...
    if storage_uri.startswith("storage/"):
        rel_path = storage_uri[len("storage/"):]
    elif storage_uri.startswith("storage\\"):
        rel_path = storage_uri[len("storage\\"):]
    else:
        rel_path = storage_uri
        
    rel_path = rel_path.replace("\\", "/")
    file_path = os.path.normpath(os.path.join(BASE_STORAGE_DIR, rel_path))
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Artifact file not found at {file_path}")
        
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        data_str = f.read()
        
    try:
        return json.loads(data_str)
    except json.JSONDecodeError:
        return data_str

def save_artifact(db, pipeline_id, task_id, artifact_type, data, metadata=None):
    """
    Saves artifact data to disk and registers it in the DB.
    Only called by the backend since it requires db connection.
    """
    from models import Artifact
    
    storage_uri, checksum = save_artifact_to_disk(pipeline_id, task_id, artifact_type, data)
    
    metadata_json = json.dumps(metadata) if metadata else None
    artifact = Artifact(
        pipeline_id=pipeline_id,
        task_id=task_id,
        artifact_type=artifact_type,
        storage_uri=storage_uri,
        metadata_json=metadata_json,
        checksum=checksum
    )
    db.add(artifact)
    db.flush()
    return artifact

def load_artifact(db, artifact_id):
    """
    Loads artifact DB record and its content from disk.
    Only called by the backend.
    """
    from models import Artifact
    artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()
    if not artifact:
        raise ValueError(f"Artifact with ID {artifact_id} not found")
        
    data = load_artifact_from_disk(artifact.storage_uri)
    return artifact, data
