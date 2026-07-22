import os
import hashlib
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from backend.platform.runtime.dependency_container import DependencyContainer
from backend.platform.api.auth import require_permission
from backend.platform.security.rate_limit import rate_limiter

router = APIRouter(tags=["Documents"])

@router.post("/documents", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    user: dict = Depends(require_permission("write:document"))
):
    # Enforce rate limit
    if rate_limiter.is_rate_limited(user["username"]):
        raise HTTPException(status_code=429, detail="Too Many Requests")

    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF uploads are allowed.")

    doc_service = DependencyContainer.get_document_service()
    doc_store = DependencyContainer.get_document_store()
    
    # Read file content to generate hash document_id
    contents = await file.read()
    hasher = hashlib.sha256(contents)
    doc_id = hasher.hexdigest()
    
    # Check if document already exists
    existing = doc_service.get_document(doc_id)
    if existing:
        return {
            "document_id": doc_id,
            "filename": existing["filename"],
            "state": existing["state"],
            "message": "Document already uploaded."
        }

    # Save to storage path
    file.file.seek(0)
    filepath = doc_store.store_document(doc_id, file.filename, file.file)
    
    # Register document
    doc = doc_service.register_document(doc_id, file.filename, filepath)
    
    return {
        "document_id": doc_id,
        "filename": doc["filename"],
        "state": doc["state"]
    }

@router.post("/documents/{document_id}/index")
async def start_indexing(
    document_id: str,
    user: dict = Depends(require_permission("write:document"))
):
    doc_service = DependencyContainer.get_document_service()
    doc = doc_service.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    # Check indexing lock
    if not doc_service.check_and_lock_document(document_id):
        raise HTTPException(status_code=409, detail="Document is currently being indexed.")
        
    indexing_service = DependencyContainer.get_indexing_service()
    job_id = indexing_service.submit_indexing_job(document_id, doc["filepath"])
    
    return {
        "document_id": document_id,
        "job_id": job_id,
        "status": "queued"
    }

@router.get("/documents/{document_id}/progress")
async def get_progress(
    document_id: str,
    user: dict = Depends(require_permission("read:document"))
):
    doc_service = DependencyContainer.get_document_service()
    doc = doc_service.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    # Query job queue
    indexing_service = DependencyContainer.get_indexing_service()
    job_id = f"job_idx_{document_id}"
    job = indexing_service.get_job_status(job_id)
    
    status_str = "unknown"
    attempts = 0
    error = None
    if job:
        status_str = job["status"]
        attempts = job["attempts"]
        error = job["error"]
    else:
        # Fallback to document record state
        status_str = doc["state"].lower()
        
    return {
        "document_id": document_id,
        "state": doc["state"],
        "job_status": status_str,
        "attempts": attempts,
        "error": error
    }
