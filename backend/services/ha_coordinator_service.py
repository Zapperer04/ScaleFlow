import uuid
import time
import os
import threading
import logging
import redis
from datetime import datetime, timedelta
from sqlalchemy import text
from models import SessionLocal, OrchestratorInstance, Pipeline, OrchestrationEvent

logger = logging.getLogger(__name__)

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# Generate unique instance ID
ORCHESTRATOR_INSTANCE_ID = f"orchestrator-{uuid.uuid4().hex[:8]}"

# Global flags
is_leader_instance = False
owned_pipelines_versions = {}          # pipeline_id -> ownership_version (Fencing Token)
owned_pipelines_lock = threading.Lock()  # protects owned_pipelines_versions
ha_thread_started = False

# Tunable constants – consider moving to config.py
OWNERSHIP_SWEEP_INTERVAL_SECONDS = 2
PIPELINE_LEASE_SECONDS = 60
HEARTBEAT_INTERVAL = 5.0
REDIS_LEASE_DURATION = 20.0

class HACoordinator:
    def __init__(self):
        self.instance_id = ORCHESTRATOR_INSTANCE_ID
        self.heartbeat_interval = HEARTBEAT_INTERVAL
        self.lease_duration = REDIS_LEASE_DURATION
        self.running = False
        self.leader_lock_key = "scaleflow:leader_lock"
        self.reconcile_callback = None          # set later to avoid circular import

    def start(self):
        global ha_thread_started
        if ha_thread_started:
            return
        self.running = True
        ha_thread_started = True

        # 1. Register self in DB
        self.register_instance()

        # 2. Start heartbeat thread
        self.heartbeat_thread = threading.Thread(target=self._run_heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()

        # 3. Start pipeline ownership and failover sweep thread
        self.ownership_thread = threading.Thread(target=self._run_ownership_loop, daemon=True)
        self.ownership_thread.start()

        print(f"[{self.instance_id}] HACoordinator started successfully.", flush=True)

    def set_reconcile_callback(self, callback):
        """Inject reconciliation callback to avoid circular import."""
        self.reconcile_callback = callback

    def register_instance(self):
        db = SessionLocal()
        try:
            # Delete stale dead instances (older than 1 minute)
            cutoff = datetime.utcnow() - timedelta(minutes=1)
            db.query(OrchestratorInstance).filter(OrchestratorInstance.last_heartbeat < cutoff).delete()

            # Register self
            inst = db.query(OrchestratorInstance).filter(OrchestratorInstance.instance_id == self.instance_id).first()
            if not inst:
                inst = OrchestratorInstance(instance_id=self.instance_id, is_leader=False, status='active')
                db.add(inst)
            else:
                inst.status = 'active'
                inst.last_heartbeat = datetime.utcnow()
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"[{self.instance_id}] Register instance error: {e}", flush=True)
        finally:
            db.close()

    def _run_heartbeat_loop(self):
        global is_leader_instance
        while self.running:
            db = SessionLocal()
            try:
                # 1. DB Heartbeat update
                inst = db.query(OrchestratorInstance).filter(OrchestratorInstance.instance_id == self.instance_id).first()
                if inst:
                    inst.last_heartbeat = datetime.utcnow()
                else:
                    inst = OrchestratorInstance(instance_id=self.instance_id, is_leader=False, status='active')
                    db.add(inst)

                # 2. Redis Heartbeat update
                redis_client.set(
                    f"scaleflow:orchestrator:{self.instance_id}:heartbeat",
                    "alive",
                    ex=int(self.lease_duration)
                )

                # 3. Leader Election try (SET NX EX)
                acquired = redis_client.set(
                    self.leader_lock_key,
                    self.instance_id,
                    nx=True,
                    ex=int(self.lease_duration)
                )
                if acquired:
                    is_leader_instance = True
                else:
                    current_leader = redis_client.get(self.leader_lock_key)
                    if current_leader == self.instance_id:
                        redis_client.expire(self.leader_lock_key, int(self.lease_duration))
                        is_leader_instance = True
                    else:
                        is_leader_instance = False

                # Update DB Leader status
                if inst:
                    inst.is_leader = is_leader_instance
                db.commit()

            except Exception as e:
                db.rollback()
                print(f"[{self.instance_id}] Heartbeat loop error: {e}", flush=True)
            finally:
                db.close()

            time.sleep(self.heartbeat_interval)

    def _run_ownership_loop(self):
        while self.running:
            db = SessionLocal()
            try:
                # 1. Renew owned pipelines leases
                self._renew_owned_pipelines(db)

                # 2. Sweep unowned/expired active pipelines to claim
                self._claim_active_pipelines(db)

            except Exception as e:
                print(f"[{self.instance_id}] Ownership loop error: {e}", flush=True)
            finally:
                db.close()
            time.sleep(OWNERSHIP_SWEEP_INTERVAL_SECONDS)

    def _renew_owned_pipelines(self, db):
        global owned_pipelines_versions
        with owned_pipelines_lock:
            pids = list(owned_pipelines_versions.keys())
        now = datetime.utcnow()
        new_expiry = now + timedelta(seconds=PIPELINE_LEASE_SECONDS)

        for pid in pids:
            try:
                pipe = db.query(Pipeline).filter(Pipeline.id == pid).first()
                if not pipe:
                    with owned_pipelines_lock:
                        owned_pipelines_versions.pop(pid, None)
                    continue

                if (pipe.owner_instance_id == self.instance_id and
                    pipe.owner_lease_expires_at is not None and
                    pipe.owner_lease_expires_at > now):
                    pipe.owner_lease_expires_at = new_expiry
                    db.commit()
                else:
                    print(f"[{self.instance_id}] Lost lease ownership of pipeline #{pid}", flush=True)
                    with owned_pipelines_lock:
                        owned_pipelines_versions.pop(pid, None)
            except Exception as e:
                db.rollback()
                print(f"[{self.instance_id}] Error renewing lease for pipeline #{pid}: {e}", flush=True)

    def _claim_active_pipelines(self, db):
        global owned_pipelines_versions
        now = datetime.utcnow()
        new_expiry = now + timedelta(seconds=PIPELINE_LEASE_SECONDS)

        # Query pipelines that are running/recovering and unowned or lease expired
        active_pipes = db.query(Pipeline).filter(
            Pipeline.status.in_(['running', 'recovering', 'created']),
            (Pipeline.owner_instance_id.is_(None)) |
            (Pipeline.owner_lease_expires_at.is_(None)) |
            (Pipeline.owner_lease_expires_at < now)
        ).all()

        for pipe in active_pipes:
            try:
                # Atomically claim ownership
                stmt = text(
                    "UPDATE pipelines "
                    "SET owner_instance_id = :my_id, owner_lease_expires_at = :expiry, ownership_version = ownership_version + 1 "
                    "WHERE id = :pid AND "
                    "  (owner_instance_id IS NULL OR owner_lease_expires_at IS NULL OR owner_lease_expires_at < :now OR owner_instance_id = :my_id)"
                )
                res = db.execute(stmt, {
                    "my_id": self.instance_id,
                    "expiry": new_expiry,
                    "now": now,
                    "pid": pipe.id
                })
                db.commit()

                if res.rowcount > 0:
                    # Re‑fetch the pipeline to get the latest version reliably (avoid overwriting loop variable)
                    claimed_pipe = db.query(Pipeline).filter(Pipeline.id == pipe.id).first()
                    if not claimed_pipe:
                        continue

                    with owned_pipelines_lock:
                        owned_pipelines_versions[claimed_pipe.id] = claimed_pipe.ownership_version

                    print(f"[{self.instance_id}] Claimed/Takeover pipeline #{claimed_pipe.id} successfully. Version token: {claimed_pipe.ownership_version}", flush=True)

                    # Log event sourcing takeover event
                    try:
                        from services.event_sourcing_service import publish_event
                        publish_event(
                            db=db,
                            event_type="PIPELINE_OWNERSHIP_TAKEN_OVER",
                            pipeline_id=claimed_pipe.id,
                            message=f"Orchestrator {self.instance_id} assumed ownership.",
                            worker_id=self.instance_id,
                            payload={"instance_id": self.instance_id, "ownership_version": claimed_pipe.ownership_version}
                        )
                        db.commit()
                    except Exception as evt_err:
                        print(f"[{self.instance_id}] Error publishing takeover event: {evt_err}", flush=True)

                    # Reconcile pipeline state immediately after takeover
                    if self.reconcile_callback:
                        try:
                            self.reconcile_callback(db)
                        except Exception as rec_err:
                            print(f"[{self.instance_id}] Error reconciling claimed pipeline #{claimed_pipe.id}: {rec_err}", flush=True)

            except Exception as e:
                db.rollback()
                print(f"[{self.instance_id}] Error claiming pipeline #{pipe.id}: {e}", flush=True)


def verify_fencing_token(db, pipeline_id):
    """
    Checks if the local orchestrator instance still owns the pipeline.
    If the pipeline is unowned or its lease has expired, the local instance
    performs an atomic JIT claim to acquire ownership.
    Raises ValueError if ownership was lost or hijacked (Fencing Conflict).
    """
    global owned_pipelines_versions
    global owned_pipelines_lock

    pipe = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
    if not pipe:
        raise ValueError(f"Pipeline #{pipeline_id} not found.")

    now = datetime.utcnow()

    # 1. JIT Claim if unowned or lease has expired
    if pipe.owner_instance_id is None or pipe.owner_lease_expires_at is None or pipe.owner_lease_expires_at < now:
        new_expiry = now + timedelta(seconds=PIPELINE_LEASE_SECONDS)
        stmt = text(
            "UPDATE pipelines "
            "SET owner_instance_id = :my_id, owner_lease_expires_at = :expiry, ownership_version = ownership_version + 1 "
            "WHERE id = :pid AND "
            "  (owner_instance_id IS NULL OR owner_lease_expires_at IS NULL OR owner_lease_expires_at < :now)"
        )
        res = db.execute(stmt, {
            "my_id": ORCHESTRATOR_INSTANCE_ID,
            "expiry": new_expiry,
            "now": now,
            "pid": pipeline_id
        })
        db.commit()
        if res.rowcount > 0:
            # Re‑fetch to get the new version, avoiding variable name conflict
            claimed_pipe = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
            if not claimed_pipe:
                raise ValueError(f"Pipeline #{pipeline_id} not found after JIT claim.")

            with owned_pipelines_lock:
                owned_pipelines_versions[pipeline_id] = claimed_pipe.ownership_version

            print(f"[{ORCHESTRATOR_INSTANCE_ID}] Atomic JIT Claim of pipeline #{pipeline_id} successfully. Version: {claimed_pipe.ownership_version}", flush=True)

            # Log event and reconcile
            try:
                from services.event_sourcing_service import publish_event
                publish_event(
                    db=db,
                    event_type="PIPELINE_OWNERSHIP_TAKEN_OVER",
                    pipeline_id=pipeline_id,
                    message=f"Orchestrator {ORCHESTRATOR_INSTANCE_ID} JIT claimed ownership.",
                    worker_id=ORCHESTRATOR_INSTANCE_ID,
                    payload={"instance_id": ORCHESTRATOR_INSTANCE_ID, "ownership_version": claimed_pipe.ownership_version}
                )
                db.commit()
                if coordinator.reconcile_callback:
                    coordinator.reconcile_callback(db)
            except Exception as e:
                print(f"Error publishing JIT claim event or reconciling: {e}", flush=True)
            return True

    # 2. Verify ownership
    if pipe.owner_instance_id != ORCHESTRATOR_INSTANCE_ID:
        raise ValueError(f"Fencing conflict: Orchestrator {ORCHESTRATOR_INSTANCE_ID} does not own pipeline #{pipeline_id}.")

    with owned_pipelines_lock:
        local_ver = owned_pipelines_versions.get(pipeline_id)
    if local_ver is None:
        raise ValueError(f"Fencing conflict: Orchestrator {ORCHESTRATOR_INSTANCE_ID} does not own pipeline #{pipeline_id} locally.")

    if pipe.ownership_version != local_ver:
        with owned_pipelines_lock:
            owned_pipelines_versions.pop(pipeline_id, None)
        raise ValueError(
            f"Fencing conflict: pipeline #{pipeline_id} ownership version mismatch! "
            f"Local token: {local_ver}, DB token: {pipe.ownership_version}. Takeover detected."
        )
    return True

# Singleton instance
coordinator = HACoordinator()