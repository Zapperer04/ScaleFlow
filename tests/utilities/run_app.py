#!/usr/bin/env python3
import os
import sys

# Add backend directory to sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

import app as flask_app
from flask import jsonify

# Monkey-patch get_artifact_content to serialize the ArtifactType enum as string
def patched_view(artifact_id):
    db = flask_app.SessionLocal()
    try:
        from context.artifact_store import load_artifact_from_disk
        from models import Artifact
        artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()
        if not artifact:
            return jsonify({"error": "Artifact not found"}), 404
        try:
            data = load_artifact_from_disk(artifact.storage_uri)
            # Serialize the enum to string (e.g. "document_graph")
            art_type_str = artifact.artifact_type.value if hasattr(artifact.artifact_type, 'value') else str(artifact.artifact_type)
            return jsonify({
                "id": artifact.id,
                "pipeline_id": artifact.pipeline_id,
                "task_id": artifact.task_id,
                "artifact_type": art_type_str,
                "content": data
            }), 200
        except Exception as e:
            return jsonify({"error": f"Failed to load file content: {str(e)}"}), 500
    finally:
        db.close()

# Replace in Flask app routing table
flask_app.app.view_functions['get_artifact_content'] = patched_view
print("Flask get_artifact_content endpoint successfully patched.", flush=True)

if __name__ == "__main__":
    port = int(os.environ.get("API_PORT", 5000))
    flask_app.app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)
