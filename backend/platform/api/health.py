from fastapi import APIRouter, Response, status
from backend.platform.runtime.app_state import app_state
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["System Health & Metrics"])

@router.get("/healthz/liveness")
async def liveness():
    # Basic check to see if fastapi is running
    return {"status": "alive"}

@router.get("/healthz/readiness")
async def readiness():
    # Check if database connection and queues are alive
    if app_state.is_healthy():
        return {"status": "ready"}
    return Response(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content='{"status": "not_ready"}'
    )

@router.get("/metrics")
async def metrics():
    # Return Prometheus metrics format
    if app_state.metrics:
        m = app_state.metrics.generate_prometheus_metrics()
        return Response(content=m, media_type="text/plain")
    return Response(content="", media_type="text/plain")
