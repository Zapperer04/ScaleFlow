import time
import json
from .core.job import JobSpec
from .core.context import ExecutionContext
from .core.events import EventType
from .core.retry import RetryPolicy
from .control_plane.interfaces import ResourceBroker, QuotaManager, LeaseManager
from .control_plane.health import ProviderStatusService, ProviderHealthService
from .data_plane.artifacts.registry import ArtifactRegistry
from .data_plane.validator.pipeline import ValidationPipeline
import logging

class ExecutionWorker:
    """
    Stateless, provider-agnostic worker loop.
    Coordinates the Control Plane and Data Plane.
    """
    def __init__(
        self,
        broker: ResourceBroker,
        quota_manager: QuotaManager,
        lease_manager: LeaseManager,
        artifact_registry: ArtifactRegistry,
        validation_pipeline: ValidationPipeline,
        status_service: ProviderStatusService,
        health_service: ProviderHealthService
    ):
        self.broker = broker
        self.quota = quota_manager
        self.lease = lease_manager
        self.registry = artifact_registry
        self.validator = validation_pipeline
        self.status = status_service
        self.health = health_service
        self.logger = logging.getLogger("Worker")

    def execute_job(self, job: JobSpec, trace_id: str) -> bool:
        """
        Executes a single job specification. Returns True on success, False on recoverable failure.
        """
        # 1. Acquire Lease (Exactly-once semantics)
        lease_id = self.lease.acquire_lease(job.id)
        if not lease_id:
            self.logger.warning(f"Failed to acquire lease for job {job.id}. Skipping.")
            return False
            
        ctx = ExecutionContext(job=job, trace_id=trace_id, lease_id=lease_id)
        ctx.emit(EventType.LEASE_ACQUIRED)
        
        provider_id = None
        start_time = time.time()
        
        try:
            # 2. Broker matches capabilities to a ResourceProvider
            provider = self.broker.acquire(job.requirements)
            provider_id = provider.get_provider_id()
            ctx.provider_id = provider_id
            ctx.emit(EventType.PROVIDER_SELECTED, {"provider": provider_id})
            
            # 3. Quota Management (Atomic Dual-Bucket)
            cost = 1 
            if not self.quota.acquire_quota(provider_id, cost=cost):
                self.logger.info(f"Quota exhausted for {provider_id}. Backing off.")
                self.status.mark_unavailable(provider_id, ttl_seconds=30)
                return False
                
            try:
                ctx.emit(EventType.PROMPT_SENT)
                
                # Mock Prompt Payload
                prompt = {"action": "parse", "schema": job.requirements.schema_version}
                
                from execution_engine.core.provider_session import ProviderSession
                session = ProviderSession(
                    provider_id=provider_id,
                    trace_id=trace_id
                )
                job.metadata['session_metrics'] = session.metrics
                
                import inspect
                inference_start = time.time()
                sig = inspect.signature(provider.parse)
                if "session" in sig.parameters:
                    raw_ast = provider.parse(job.payload, prompt_payload=prompt, session=session)
                else:
                    raw_ast = provider.parse(job.payload, prompt_payload=prompt)
                inference_time = time.time() - inference_start
                session.record_duration("inference_time_ms", inference_time)
                session.finalize()
                
                raw_json_str = json.dumps(raw_ast)
                
                # 4. Validation & Normalization Pipeline
                canonical_graph = self.validator.validate(raw_json_str, ctx)
                
                # 5. Artifact Storage
                content_bytes = json.dumps(canonical_graph).encode('utf-8')
                result_artifact = self.registry.store(
                    content=content_bytes,
                    content_type="application/json",
                    version="v1"
                )
                
                # Record successful health metrics
                self.health.record_metrics(provider_id, latency=inference_time, success=True)
                
                # Record day-one metrics
                ctx.emit(EventType.ARTIFACT_WRITTEN, {
                    "uri": result_artifact.uri,
                    "inference_time_ms": int(inference_time * 1000),
                    "total_time_ms": int((time.time() - start_time) * 1000)
                })
                return True
                
            finally:
                self.quota.release_quota(provider_id, cost=cost)
                
        except Exception as e:
            # Record failed health metrics
            if provider_id:
                is_malformed = "malformed" in str(e).lower()
                self.health.record_metrics(provider_id, latency=time.time() - start_time, success=False, malformed=is_malformed)
                
            retry_action = RetryPolicy.classify(e)
            ctx.emit(EventType.JOB_FAILED, {
                "error": str(e),
                "should_retry": retry_action.should_retry,
                "is_fatal": retry_action.is_fatal
            })
            
            if retry_action.mark_unavailable and provider_id:
                self.status.mark_unavailable(provider_id, ttl_seconds=60)
                
            if retry_action.is_fatal:
                self.logger.error(f"Fatal job error: {e}")
                raise e
            return False
            
        finally:
            self.lease.release_lease(job.id, lease_id)
            ctx.emit(EventType.LEASE_RELEASED)
