import uuid
import logging
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from backend.platform.config.settings import settings
from backend.platform.runtime.startup import platform_startup
from backend.platform.runtime.shutdown import platform_shutdown

logger = logging.getLogger(__name__)

app = FastAPI(
    title="MR-RAG Serving Platform",
    description="Production serving platform around the frozen hybrid MR-RAG engine.",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup / Shutdown Hooks
@app.on_event("startup")
def startup_event():
    platform_startup()

@app.on_event("shutdown")
def shutdown_event():
    platform_shutdown()

# Request ID propagation middleware
@app.middleware("http")
async def add_request_headers(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
    
    # Store in request state for downstream handlers
    request.state.request_id = request_id
    request.state.trace_id = trace_id
    
    response: Response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Trace-ID"] = trace_id
    return response

# Register Sub-routers
from backend.platform.api.auth import router as auth_router
from backend.platform.api.upload import router as upload_router
from backend.platform.api.query import router as query_router
from backend.platform.api.health import router as health_router
from backend.platform.api.websocket import router as ws_router
from backend.platform.api.admin import router as admin_router

app.include_router(auth_router, prefix=settings.API_VERSION_PREFIX)
app.include_router(upload_router, prefix=settings.API_VERSION_PREFIX)
app.include_router(query_router, prefix=settings.API_VERSION_PREFIX)
app.include_router(health_router, prefix=settings.API_VERSION_PREFIX)
app.include_router(ws_router, prefix=settings.API_VERSION_PREFIX)
app.include_router(admin_router, prefix=settings.API_VERSION_PREFIX)
