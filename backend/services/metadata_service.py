import json
import os
import sys

# Adjust path to find models and config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import Pipeline, Artifact

def get_standardized_metadata(db, pipeline_id: int) -> dict:
    """
    Retrieve standardized, domain-agnostic metadata for a pipeline.
    
    Parameters
    ----------
    db          : database session
    pipeline_id : target pipeline id
    
    Returns
    -------
    Dictionary of standardized metadata fields.
    """
    pipeline = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
    if not pipeline:
        return {}
        
    artifacts = db.query(Artifact).filter(Artifact.pipeline_id == pipeline_id).all()
    
    document_type = "generic"
    parser_used = "unknown"
    quality_score = 0.0
    chunk_count = 0
    embedding_count = 0
    
    for art in artifacts:
        meta = art.metadata_json
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except:
                meta = {}
        elif not isinstance(meta, dict):
            meta = {}
            
        if art.artifact_type == "uploaded_file":
            orig_filename = meta.get("original_filename", "").lower()
            if "paper" in orig_filename:
                document_type = "research_paper"
            elif "contract" in orig_filename:
                document_type = "legal_contract"
            elif "assign" in orig_filename:
                document_type = "assignment"
            elif "book" in orig_filename or "sure_thing" in orig_filename:
                document_type = "book"
            elif orig_filename.endswith(".log"):
                document_type = "log_file"
            else:
                document_type = "document"
                
        elif art.artifact_type == "parsed_text":
            parser_used = meta.get("parser_used") or meta.get("selected_parser") or parser_used
            quality_score = meta.get("coherence_score") or meta.get("quality_score") or quality_score
            
        elif art.artifact_type == "text_chunks":
            chunk_count = meta.get("chunk_count") or len(meta.get("chunks", [])) or chunk_count
            if not chunk_count:
                try:
                    from context.artifact_store import load_artifact_from_disk
                    content = load_artifact_from_disk(art.storage_uri)
                    if isinstance(content, list):
                        chunk_count = len(content)
                except:
                    pass
                    
        elif art.artifact_type == "vector_index":
            embedding_count = meta.get("vector_count") or embedding_count
            
    return {
        "document_type": document_type,
        "parser_used": str(parser_used),
        "quality_score": round(float(quality_score), 2) if quality_score is not None else 0.0,
        "chunk_count": int(chunk_count),
        "embedding_count": int(embedding_count)
    }
