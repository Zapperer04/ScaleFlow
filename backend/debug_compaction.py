"""
One-shot diagnostic: runs compact_completed_pipeline_segments once and prints
the full traceback if it fails.
"""
import traceback
import sys
import os

# Ensure the backend directory is on the path
sys.path.insert(0, os.path.dirname(__file__))

from database import SessionLocal
from services.event_sourcing_service import compact_completed_pipeline_segments

db = SessionLocal()
try:
    print("[DEBUG] Running compact_completed_pipeline_segments...", flush=True)
    compact_completed_pipeline_segments(db)
    print("[DEBUG] Compaction completed with NO errors.", flush=True)
except Exception as e:
    print(f"[DEBUG] EXCEPTION: {e}", flush=True)
    print(f"[DEBUG] Full traceback:", flush=True)
    traceback.print_exc()
finally:
    db.close()
