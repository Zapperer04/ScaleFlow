"""
ExecutionWorker — Phase 2C
Integrates: AdaptiveRateLimitManager, CircuitBreaker, AdaptiveCooldownScheduler,
enhanced ProviderHealthService, FailureAnalysis.

KEY: HTTP 429 is treated as a quota policy event — the worker reports it,
routes elsewhere, and does NOT count it as a correctness failure.
"""
import time
import json
import logging
from typing import Optional

from .core.job import JobSpec
from .core.context import ExecutionContext
from .core.events import EventType
from .core.retry import RetryPolicy
from .control_plane.interfaces import ResourceBroker, QuotaManager, LeaseManager
from .control_plane.health import ProviderStatusService, ProviderHealthService
from .control_plane.circuit_breaker import (
    get_circuit_registry, get_cooldown_scheduler, CircuitState
)
from .control_plane.adaptive_rate_manager import get_adaptive_rate_manager
from .data_plane.artifacts.registry import ArtifactRegistry
from .data_plane.validator.pipeline import ValidationPipeline
from .data_plane.adapters.gemini_client import RateLimitError, TransportError, SchemaError


class ExecutionWorker:
    """
    Stateless, provider-agnostic worker loop.
    Coordinates the Control Plane and Data Plane.
    Reports quota events separately from engine correctness failures.
    """

    def __init__(
        self,
        broker: ResourceBroker,
        quota_manager: QuotaManager,
        lease_manager: LeaseManager,
        artifact_registry: ArtifactRegistry,
        validation_pipeline: ValidationPipeline,
        status_service: ProviderStatusService,
        health_service: ProviderHealthService,
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
        Executes a single job specification.
        Returns True on success, False on recoverable failure.
        Raises on fatal (auth, safety) errors.
        """
        # 1. Acquire lease (exactly-once semantics)
        lease_id = self.lease.acquire_lease(job.id)
        if not lease_id:
            self.logger.warning(f"Failed to acquire lease for job {job.id}. Skipping.")
            return False

        ctx = ExecutionContext(job=job, trace_id=trace_id, lease_id=lease_id)
        ctx.emit(EventType.LEASE_ACQUIRED)

        provider_id: Optional[str] = None
        start_time = time.time()

        try:
            # 2. Broker — capabilities + circuit breaker + cooldown + rate limit
            provider = self.broker.acquire(job.requirements)
            provider_id = provider.get_provider_id()
            ctx.provider_id = provider_id
            ctx.emit(EventType.PROVIDER_SELECTED, {"provider": provider_id})

            # 3. Quota Management (Atomic Dual-Bucket)
            cost = 1
            if not self.quota.acquire_quota(provider_id, cost=cost):
                self.logger.info(f"Quota exhausted for {provider_id}. Backing off.")
                self.status.mark_unavailable(provider_id, ttl_seconds=30, reason="quota_bucket_empty")
                get_cooldown_scheduler().register_429(provider_id, retry_after=30.0)
                get_circuit_registry().get(provider_id).record_429(retry_after=30.0)
                return False

            try:
                ctx.emit(EventType.PROMPT_SENT)
                prompt = {"action": "parse", "schema": job.requirements.schema_version}

                from execution_engine.core.provider_session import ProviderSession
                session = ProviderSession(provider_id=provider_id, trace_id=trace_id)
                job.metadata["session_metrics"] = session.metrics

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
                content_bytes = json.dumps(canonical_graph).encode("utf-8")
                result_artifact = self.registry.store(
                    content=content_bytes,
                    content_type="application/json",
                    version="v1",
                )

                # Record success in all subsystems
                self.health.record_metrics(
                    provider_id,
                    latency=inference_time,
                    success=True,
                    was_retry="retry" in job.id.lower(),
                )
                get_circuit_registry().get(provider_id).record_success()
                total_time = time.time() - start_time
                get_adaptive_rate_manager().record_success(
                    provider_id,
                    tokens=session.metrics.get("input_tokens", 0),
                    latency_ms=inference_time * 1000.0,
                    queue_wait_ms=max(0.0, total_time - inference_time) * 1000.0
                )

                ctx.emit(EventType.ARTIFACT_WRITTEN, {
                    "uri": result_artifact.uri,
                    "inference_time_ms": int(inference_time * 1000),
                    "total_time_ms": int((time.time() - start_time) * 1000),
                })
                return True

            finally:
                self.quota.release_quota(provider_id, cost=cost)

        except RateLimitError as e:
            # 429 — quota policy event, NOT a correctness failure
            retry_after = e.retry_after or 60.0
            self.logger.warning(
                f"[Worker] 429 from {provider_id}: Retry-After={retry_after:.0f}s. "
                f"Applying cooldown, routing elsewhere."
            )

            if provider_id:
                self.health.record_metrics(
                    provider_id,
                    latency=time.time() - start_time,
                    success=False,
                    is_429=True,
                )
                self.status.mark_unavailable(
                    provider_id,
                    ttl_seconds=int(retry_after) + 5,
                    reason="HTTP_429_QUOTA",
                )
                get_cooldown_scheduler().register_429(provider_id, retry_after=retry_after)
                get_circuit_registry().get(provider_id).record_429(retry_after=retry_after)
                get_adaptive_rate_manager().record_429(provider_id, retry_after=retry_after)

            ctx.emit(EventType.JOB_FAILED, {
                "error": str(e),
                "failure_layer": "Provider",
                "root_cause": "HTTP_429_QUOTA_EXHAUSTED",
                "is_quota_event": True,
                "cooldown_applied": True,
                "broker_decision": "ROUTE_ELSEWHERE",
                "should_retry": True,
                "is_fatal": False,
            })
            return False

        except Exception as e:
            elapsed = time.time() - start_time
            is_429 = "429" in str(e).lower() or "rate limit" in str(e).lower()
            is_timeout = "timeout" in str(e).lower()

            if provider_id:
                is_malformed = "malformed" in str(e).lower() or "json" in str(e).lower()
                self.health.record_metrics(
                    provider_id,
                    latency=elapsed,
                    success=False,
                    malformed=is_malformed,
                    is_429=is_429,
                    is_timeout=is_timeout,
                )

            retry_action = RetryPolicy.classify(e)
            analysis = retry_action.analysis

            ctx.emit(EventType.JOB_FAILED, {
                "error": str(e),
                "failure_layer": analysis.failure_layer if analysis else "Unknown",
                "root_cause": analysis.root_cause if analysis else "Unknown",
                "retry_decision": analysis.retry_decision if analysis else "RETRY_BACKOFF",
                "cooldown_applied": analysis.cooldown_applied if analysis else False,
                "broker_decision": analysis.broker_decision if analysis else "ROUTE_ELSEWHERE",
                "is_quota_event": analysis.is_quota_event if analysis else False,
                "should_retry": retry_action.should_retry,
                "is_fatal": retry_action.is_fatal,
            })

            if retry_action.mark_unavailable and provider_id:
                reason = analysis.root_cause if analysis else "failure"
                self.status.mark_unavailable(provider_id, ttl_seconds=60, reason=reason)
                if is_429:
                    get_cooldown_scheduler().register_429(provider_id)
                    get_circuit_registry().get(provider_id).record_429()
                elif analysis and analysis.failure_layer in ("Transport",):
                    get_circuit_registry().get(provider_id).record_failure(str(e))

            if retry_action.is_fatal:
                self.logger.error(f"Fatal job error: {e}")
                raise e

            return False

        finally:
            self.lease.release_lease(job.id, lease_id)
            ctx.emit(EventType.LEASE_RELEASED)
