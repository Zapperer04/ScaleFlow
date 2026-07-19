import os
import time
import json
import redis
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Import execution engine core & control plane components
from execution_engine.worker import ExecutionWorker
from execution_engine.control_plane.broker import DefaultResourceBroker
from execution_engine.control_plane.capabilities import YamlCapabilityRegistry
from execution_engine.control_plane.health import ProviderStatusService, ProviderHealthService
from execution_engine.control_plane.lease_manager import RedisLeaseManager
from execution_engine.control_plane.quota_manager import RedisQuotaManager
from execution_engine.data_plane.artifacts.local_registry import LocalArtifactRegistry
from execution_engine.data_plane.validator.pipeline import ValidationPipeline
from execution_engine.data_plane.normalizer.graph import GraphNormalizer
from execution_engine.simulation.sim_adapters import SimulatedGeminiAdapter, SimulatedOpenRouterAdapter
from execution_engine.core.job import JobSpec
from execution_engine.core.events import EventEmitter, ExecutionEvent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("WorkerDaemon")

WORKER_ID = os.environ.get("WORKER_ID", "worker-1")
REDIS_HOST = os.environ.get("REDIS_HOST", "redis-proxy")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6381))

# Initialize Redis
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

# Worker State Tracking
class WorkerStateTracker:
    def __init__(self):
        self.state = "idle"
        self.state_durations = {
            "idle": 0.0,
            "inference": 0.0,
            "validation": 0.0,
            "normalization": 0.0,
            "artifact": 0.0
        }
        self.last_state_change = time.time()
        self.lock = threading.Lock()
        
    def transition_to(self, new_state):
        with self.lock:
            now = time.time()
            duration = now - self.last_state_change
            self.state_durations[self.state] += duration
            self.state = new_state
            self.last_state_change = now
            logger.info(f"[{WORKER_ID}] State transition: {self.state} -> {new_state}")
        
    def get_ratios(self):
        with self.lock:
            now = time.time()
            duration = now - self.last_state_change
            self.state_durations[self.state] += duration
            self.last_state_change = now
            
            total = sum(self.state_durations.values())
            if total == 0:
                return {k: 0.0 for k in self.state_durations}
            return {k: self.state_durations[k] / total for k in self.state_durations}

state_tracker = WorkerStateTracker()

# Metrics collection
metrics = {
    "broker_decision_latency_sum": 0.0,
    "broker_decisions_count": 0,
    "broker_rejected_providers_total": 0,
    "lease_acquisition_latency_sum": 0.0,
    "lease_acquires_count": 0,
    "lease_active_leases": 0,
    "lease_expired_leases_total": 0,
    "jobs_processed": 0
}

# Hook into EventEmitter
def simulation_event_listener(event: ExecutionEvent):
    # Push to Redis for replay recording
    try:
        r.rpush("simulation:events", event.model_dump_json())
    except Exception as e:
        logger.error(f"Failed to push event to Redis: {e}")

    # Track State transitions
    if event.type.value in ["LEASE_ACQUIRED", "PROVIDER_SELECTED"]:
        state_tracker.transition_to("inference")
    elif event.type.value == "JSON_VALIDATED":
        state_tracker.transition_to("validation")
    elif event.type.value == "ARTIFACT_WRITTEN":
        state_tracker.transition_to("artifact")
    elif event.type.value in ["LEASE_RELEASED", "JOB_FAILED"]:
        state_tracker.transition_to("idle")

EventEmitter.register_listener(simulation_event_listener)

# Wrap LeaseManager and Broker to record metrics
class MetricLeaseManager(RedisLeaseManager):
    def acquire_lease(self, job_id: str, ttl_seconds: int = 300):
        start = time.time()
        res = super().acquire_lease(job_id, ttl_seconds)
        latency = time.time() - start
        metrics["lease_acquisition_latency_sum"] += latency
        metrics["lease_acquires_count"] += 1
        if res:
            metrics["lease_active_leases"] += 1
        return res

    def release_lease(self, job_id: str, lease_id: str):
        res = super().release_lease(job_id, lease_id)
        if res and metrics["lease_active_leases"] > 0:
            metrics["lease_active_leases"] -= 1
        return res

# Prometheus Metrics HTTP Server
class MetricsHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass # Suppress standard access logs to keep terminal clean

    def do_GET(self):
        if self.path == "/metrics":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.end_headers()
            
            # Gather metrics
            ratios = state_tracker.get_ratios()
            
            # Read quota utilization
            rpm_gemini = r.get("quota:gemini:rpm") or b"0"
            rpd_gemini = r.get("quota:gemini:rpd") or b"0"
            concurrent_gemini = r.get("quota:gemini:concurrent") or b"0"
            
            rpm_openrouter = r.get("quota:openrouter:rpm") or b"0"
            rpd_openrouter = r.get("quota:openrouter:rpd") or b"0"
            concurrent_openrouter = r.get("quota:openrouter:concurrent") or b"0"
            
            # Read queue status
            qlen = r.llen("simulation:jobs")
            
            lines = [
                # Worker ratios
                f'worker_idle_ratio{{worker="{WORKER_ID}"}} {ratios["idle"]}',
                f'worker_inference_ratio{{worker="{WORKER_ID}"}} {ratios["inference"]}',
                f'worker_validation_ratio{{worker="{WORKER_ID}"}} {ratios["validation"]}',
                f'worker_normalization_ratio{{worker="{WORKER_ID}"}} {ratios["normalization"]}',
                f'worker_artifact_ratio{{worker="{WORKER_ID}"}} {ratios["artifact"]}',
                
                # Lease Metrics
                f'lease_acquisition_latency_seconds_sum{{worker="{WORKER_ID}"}} {metrics["lease_acquisition_latency_sum"]}',
                f'lease_active_leases{{worker="{WORKER_ID}"}} {metrics["lease_active_leases"]}',
                
                # Quota Metrics
                f'quota_rpm_utilization{{provider="gemini"}} {rpm_gemini.decode()}',
                f'quota_rpd_utilization{{provider="gemini"}} {rpd_gemini.decode()}',
                f'quota_semaphore_utilization{{provider="gemini"}} {concurrent_gemini.decode()}',
                
                f'quota_rpm_utilization{{provider="openrouter"}} {rpm_openrouter.decode()}',
                f'quota_rpd_utilization{{provider="openrouter"}} {rpd_openrouter.decode()}',
                f'quota_semaphore_utilization{{provider="openrouter"}} {concurrent_openrouter.decode()}',
                
                # Queue metrics
                f'queue_depth {qlen}',
                
                # General count
                f'jobs_processed_total{{worker="{WORKER_ID}"}} {metrics["jobs_processed"]}'
            ]
            self.wfile.write(("\n".join(lines) + "\n").encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

def start_metrics_server():
    port = int(os.environ.get("METRICS_PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), MetricsHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    logger.info(f"Prometheus metrics exporter started on port {port}")

def main():
    logger.info(f"Starting worker daemon {WORKER_ID} connecting to Redis at {REDIS_HOST}:{REDIS_PORT}")
    start_metrics_server()

    # Wait for Redis
    for _ in range(30):
        try:
            r.ping()
            break
        except Exception:
            time.sleep(1)
            
    # Initialize Engine Components
    manifests_dir = os.environ.get("MANIFESTS_DIR", "execution_engine/core/manifests")
    registry = YamlCapabilityRegistry(manifests_dir=manifests_dir)
    status_service = ProviderStatusService(r)
    health_service = ProviderHealthService(r)
    
    # Initialize providers
    gemini_provider = SimulatedGeminiAdapter()
    openrouter_provider = SimulatedOpenRouterAdapter()
    providers = [gemini_provider, openrouter_provider]
    
    # Broker
    broker = DefaultResourceBroker(
        providers=providers,
        registry=registry,
        status_service=status_service,
        health_service=health_service
    )
    
    # Hook broker decisions
    def broker_decision_listener(decision):
        metrics["broker_decisions_count"] += 1
        try:
            r.rpush("simulation:broker_decisions", json.dumps(decision))
        except Exception as e:
            logger.error(f"Failed to log broker decision: {e}")
            
    broker.decision_listeners = [broker_decision_listener]
    
    # Quota, Lease, Artifacts, Validation
    quota_manager = RedisQuotaManager(r, max_concurrent=3)
    lease_manager = MetricLeaseManager(r)
    
    artifact_registry = LocalArtifactRegistry(base_dir="/tmp/scaleflow/artifacts")
    normalizer = GraphNormalizer()
    validation_pipeline = ValidationPipeline(normalizer)
    
    # Worker
    worker = ExecutionWorker(
        broker=broker,
        quota_manager=quota_manager,
        lease_manager=lease_manager,
        artifact_registry=artifact_registry,
        validation_pipeline=validation_pipeline,
        status_service=status_service,
        health_service=health_service
    )
    
    # Main Daemon Loop
    while True:
        try:
            # BLPOP job
            res = r.blpop("simulation:jobs", timeout=2)
            if not res:
                continue
                
            _, job_data_str = res
            job_dict = json.loads(job_data_str.decode("utf-8"))
            job = JobSpec(**job_dict)
            
            trace_id = f"sim-trace-{job.id}-{int(time.time())}"
            logger.info(f"[{WORKER_ID}] Picked up job {job.id}. Executing...")
            
            success = worker.execute_job(job, trace_id)
            metrics["jobs_processed"] += 1
            logger.info(f"[{WORKER_ID}] Job {job.id} execution result: {success}")
            
        except Exception as e:
            logger.error(f"Error in worker daemon loop: {e}", exc_info=True)
            time.sleep(1)

if __name__ == "__main__":
    main()
