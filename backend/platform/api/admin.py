from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List
from backend.platform.api.auth import require_permission
from backend.platform.config.limits import FEATURE_FLAGS
from backend.platform.runtime.app_state import app_state

router = APIRouter(prefix="/admin", tags=["Admin Operations"])

@router.get("/queues")
async def get_queue_stats(user: dict = Depends(require_permission("admin"))):
    conn = app_state.db_conn
    cursor = conn.cursor()
    cursor.execute("""
    SELECT status, COUNT(*) as count FROM job_queue GROUP BY status
    """)
    rows = cursor.fetchall()
    stats = {r["status"]: r["count"] for r in rows}
    return {
        "queue_backend": "sqlite",
        "jobs": stats
    }

@router.get("/workers")
async def get_workers(user: dict = Depends(require_permission("admin"))):
    conn = app_state.db_conn
    cursor = conn.cursor()
    cursor.execute("""
    SELECT worker_id, status, last_heartbeat FROM worker_registry
    """)
    rows = cursor.fetchall()
    return [{"worker_id": r["worker_id"], "status": r["status"], "last_heartbeat": r["last_heartbeat"]} for r in rows]

@router.get("/feature-flags")
async def get_feature_flags(user: dict = Depends(require_permission("admin"))):
    return FEATURE_FLAGS

@router.post("/feature-flags/{flag_name}")
async def toggle_feature_flag(
    flag_name: str,
    enabled: bool,
    user: dict = Depends(require_permission("admin"))
):
    if flag_name not in FEATURE_FLAGS:
        raise HTTPException(status_code=404, detail="Feature flag not found")
    FEATURE_FLAGS[flag_name] = enabled
    return {"flag": flag_name, "enabled": enabled}

@router.get("/costs")
async def get_cost_summary(user: dict = Depends(require_permission("admin"))):
    conn = app_state.db_conn
    cursor = conn.cursor()
    cursor.execute("""
    SELECT provider, model, SUM(prompt_tokens) as total_prompt, SUM(completion_tokens) as total_completion, SUM(cost) as total_cost
    FROM cost_logs GROUP BY provider, model
    """)
    rows = cursor.fetchall()
    
    total_cost = 0.0
    details = []
    for r in rows:
        total_cost += r["total_cost"]
        details.append({
            "provider": r["provider"],
            "model": r["model"],
            "prompt_tokens": r["total_prompt"],
            "completion_tokens": r["total_completion"],
            "cost": r["total_cost"]
        })
        
    return {
        "total_cost_usd": total_cost,
        "details": details
    }
