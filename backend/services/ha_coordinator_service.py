import uuid
import time
import os
import threading
import logging
import redis
from datetime import datetime, timedelta
from sqlalchemy import text
from models import SessionLocal, OrchestratorInstance, Pipeline

logger = logging.getLogger(__name__)

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Redis configuration with fallback
REDIS_HOST = os.environ.get("REDIS_HOST", getattr(config, "REDIS_HOST", "localhost"))
REDIS_PORT = int(os.environ.get("REDIS_PORT", getattr(config, "REDIS_PORT", 6379)))
REDIS_DB = int(os.environ.get("REDIS_DB", getattr(config, "REDIS_DB", 0)))

# HA constants (overridable from config)
OWNERSHIP_SWEEP_INTERVAL_SECONDS = getattr(config, "OWNERSHIP_SWEEP_INTERVAL_SECONDS", 5)
PIPELINE_LEASE_SECONDS = getattr(config, "PIPELINE_LEASE_SECONDS", 120)
HEARTBEAT_INTERVAL = getattr(config, "HEARTBEAT_INTERVAL", 15.0)
REDIS_LEASE_DURATION = getattr(config, "REDIS_LEASE_DURATION", 30.0)
REDIS_RETRY_COUNT = getattr(config, "REDIS_RETRY_COUNT", 3)
REDIS_RETRY_BACKOFF = getattr(config, "REDIS_RETRY_BACKOFF", 0.5)

# Redis client with retry
def _get_redis_client():
    for attempt in range(REDIS_RETRY_COUNT):
        try:
            client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
            client.ping()
            return client
        except Exception as e:
            if attempt == REDIS_RETRY_COUNT - 1:
                logger.warning(f"Redis unavailable after {REDIS_RETRY_COUNT} attempts: {e}")
                return None
            time.sleep(REDIS_RETRY_BACKOFF * (2 ** attempt))
    return None

redis_client = _get_redis_client()

# Generate unique instance ID
ORCHESTRATOR_INSTANCE_ID = f"orchestrator-{uuid.uuid4().hex[:8]}"

# Global flags
is_leader_instance = False
owned_pipelines_versions = {}          # pipeline_id -> ownership_version (Fencing Token)
owned_pipelines_lock = threading.Lock()  # protects owned_pipelines_versions
ha_thread_started = False

class HACoordinator:
    def __init__(self):
        self.instance_id = ORCHESTRATOR_INSTANCE_ID
        self.heartbeat_interval = HEARTBEAT_INTERVAL
        self.lease_duration = REDIS_LEASE_DURATION
        self.running = False
        self.leader_lock_key = "scaleflow:leader_lock"
        self.reconcile_callback = None          # set later to avoid circular import
        self._previous_leader_state = False      # for Redis failure fallback
        self._redis_healthy = True

    def start(self):
        global ha_thread_started
        if ha_thread_started:
            return
        self.running = True
        ha_thread_started = True

        # 1. Register self in DB
        self.register_instance()

        # 2. Rebuild ownership cache from database
        self._rebuild_ownership_cache()

        # 3. Start heartbeat thread
        self.heartbeat_thread = threading.Thread(target=self._run_heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()

        # 4. Start pipeline ownership and failover sweep thread
        self.ownership_thread = threading.Thread(target=self._run_ownership_loop, daemon=True)
        self.ownership_thread.start()

        logger.info(f"[{self.instance_id}] HACoordinator started successfully.")

    def _rebuild_ownership_cache(self):
        """Rebuild the in-memory ownership map from database on startup."""
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            owned = db.query(Pipeline).filter(
                Pipeline.owner_instance_id == self.instance_id,
                Pipeline.owner_lease_expires_at > now
            ).all()
            with owned_pipelines_lock:
                owned_pipelines_versions.clear()
                for p in owned:
                    owned_pipelines_versions[p.id] = p.ownership_version
            logger.info(f"[{self.instance_id}] Rebuilt ownership cache: {len(owned)} pipelines.")
        except Exception as e:
            logger.error(f"[{self.instance_id}] Failed to rebuild ownership cache: {e}")
        finally:
            db.close()

    def set_reconcile_callback(self, callback):
        self.reconcile_callback = callback

    def register_instance(self):
        db = SessionLocal()
        try:
            # Delete stale dead instances (older than 2 minutes)
            cutoff = datetime.utcnow() - timedelta(minutes=2)
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
            logger.error(f"[{self.instance_id}] Register instance error: {e}")
        finally:
            db.close()

    def _run_heartbeat_loop(self):
        global is_leader_instance
        heartbeat_counter = 0
        while self.running:
            db = SessionLocal()
            try:
                heartbeat_counter += 1
                inst = db.query(OrchestratorInstance).filter(OrchestratorInstance.instance_id == self.instance_id).first()
                if inst:
                    inst.last_heartbeat = datetime.utcnow()
                else:
                    inst = OrchestratorInstance(instance_id=self.instance_id, is_leader=False, status='active')
                    db.add(inst)

                # Update DB leader status every heartbeat (but we might reduce writes by doing it every N)
                # For simplicity, we update every time.
                # Redis Heartbeat update with retry
                redis_ok = False
                global redis_client
                if redis_client is None:
                    redis_client = _get_redis_client()
                for attempt in range(REDIS_RETRY_COUNT):
                    try:
                        if redis_client is not None:
                            redis_client.set(
                                f"scaleflow:orchestrator:{self.instance_id}:heartbeat",
                                "alive",
                                ex=int(self.lease_duration)
                            )
                            acquired = redis_client.set(
                                self.leader_lock_key,
                                self.instance_id,
                                nx=True,
                                ex=int(self.lease_duration)
                            )
                            if acquired:
                                is_leader_instance = True
                                self._previous_leader_state = True
                                self._redis_healthy = True
                            else:
                                current_leader = redis_client.get(self.leader_lock_key)
                                if current_leader == self.instance_id:
                                    redis_client.expire(self.leader_lock_key, int(self.lease_duration))
                                    is_leader_instance = True
                                    self._previous_leader_state = True
                                else:
                                    is_leader_instance = False
                                    self._previous_leader_state = False
                            redis_ok = True
                            self._redis_healthy = True
                            break
                    except Exception as e:
                        logger.warning(f"[{self.instance_id}] Redis operation attempt {attempt+1} failed: {e}")
                        time.sleep(REDIS_RETRY_BACKOFF * (2 ** attempt))
                        redis_client = _get_redis_client()
                if not redis_ok:
                    is_leader_instance = self._previous_leader_state
                    self._redis_healthy = False
                    logger.warning(f"[{self.instance_id}] Redis unavailable; leader state preserved: {is_leader_instance}")

                if inst:
                    inst.is_leader = is_leader_instance
                db.commit()

            except Exception as e:
                db.rollback()
                logger.error(f"[{self.instance_id}] Heartbeat loop error: {e}")
            finally:
                db.close()

            time.sleep(self.heartbeat_interval)

    def _run_ownership_loop(self):
        while self.running:
            db = SessionLocal()
            try:
                # 1. Renew owned pipelines leases in a single batch
                self._renew_owned_pipelines_batch(db)

                # 2. Claim unowned/expired active pipelines in a single batch
                self._claim_active_pipelines_batch(db)

            except Exception as e:
                logger.error(f"[{self.instance_id}] Ownership loop error: {e}")
            finally:
                db.close()
            time.sleep(OWNERSHIP_SWEEP_INTERVAL_SECONDS)

    def _renew_owned_pipelines_batch(self, db):
        """Batch renew all owned pipelines in one UPDATE."""
        global owned_pipelines_versions
        with owned_pipelines_lock:
            pids = list(owned_pipelines_versions.keys())
        if not pids:
            return
        now = datetime.utcnow()
        new_expiry = now + timedelta(seconds=PIPELINE_LEASE_SECONDS)

        try:
            stmt = text(
                "UPDATE pipelines "
                "SET owner_lease_expires_at = :expiry "
                "WHERE id = ANY(:pids) "
                "  AND owner_instance_id = :my_id "
                "  AND owner_lease_expires_at > :now"
            )
            res = db.execute(stmt, {
                "expiry": new_expiry,
                "pids": pids,
                "my_id": self.instance_id,
                "now": now
            })
            db.commit()
            logger.debug(f"[{self.instance_id}] Renewed leases for {res.rowcount} pipelines.")
            if res.rowcount < len(pids):
                still_owned = db.query(Pipeline.id).filter(
                    Pipeline.id.in_(pids),
                    Pipeline.owner_instance_id == self.instance_id,
                    Pipeline.owner_lease_expires_at > now
                ).all()
                owned_set = {p[0] for p in still_owned}
                with owned_pipelines_lock:
                    for pid in list(owned_pipelines_versions.keys()):
                        if pid not in owned_set:
                            del owned_pipelines_versions[pid]
        except Exception as e:
            db.rollback()
            logger.error(f"[{self.instance_id}] Batch renew error: {e}")

    def _claim_active_pipelines_batch(self, db):
        """
        Batch claim all claimable pipelines in one UPDATE, returning only those newly claimed.
        Uses RETURNING to capture the IDs and versions of rows that were updated.
        """
        global owned_pipelines_versions
        now = datetime.utcnow()
        new_expiry = now + timedelta(seconds=PIPELINE_LEASE_SECONDS)

        try:
            stmt = text(
                "UPDATE pipelines "
                "SET owner_instance_id = :my_id, "
                "    owner_lease_expires_at = :expiry, "
                "    ownership_version = ownership_version + 1 "
                "WHERE status IN ('running', 'recovering', 'created') "
                "  AND (owner_instance_id IS NULL OR owner_lease_expires_at IS NULL OR owner_lease_expires_at < :now) "
                "  AND (owner_instance_id != :my_id OR owner_lease_expires_at IS NULL OR owner_lease_expires_at < :now) "
                "RETURNING id, ownership_version"
            )
            result = db.execute(stmt, {
                "my_id": self.instance_id,
                "expiry": new_expiry,
                "now": now
            })
            # Fetch all rows that were actually updated
            claimed_rows = result.fetchall()
            db.commit()

            if claimed_rows:
                newly_claimed = []
                for row in claimed_rows:
                    pid = row[0]
                    version = row[1]
                    # Add to cache
                    with owned_pipelines_lock:
                        owned_pipelines_versions[pid] = version
                    newly_claimed.append((pid, version))
                    logger.info(f"[{self.instance_id}] Batch claimed pipeline #{pid}. Version: {version}")

                # Publish events and reconcile in a single batch
                if newly_claimed:
                    # Publish events
                    try:
                        from services.event_sourcing_service import publish_event
                        for pid, version in newly_claimed:
                            publish_event(
                                db=db,
                                event_type="PIPELINE_OWNERSHIP_TAKEN_OVER",
                                pipeline_id=pid,
                                message=f"Orchestrator {self.instance_id} assumed ownership (batch).",
                                worker_id=self.instance_id,
                                payload={"instance_id": self.instance_id, "ownership_version": version}
                            )
                        db.commit()
                    except Exception as evt_err:
                        logger.error(f"[{self.instance_id}] Error publishing takeover events: {evt_err}")
                        # Still attempt to reconcile even if event publishing fails
                    # Reconcile once for all claimed pipelines
                    if self.reconcile_callback:
                        try:
                            self.reconcile_callback(db)
                        except Exception as rec_err:
                            logger.error(f"[{self.instance_id}] Error reconciling after batch claim: {rec_err}")

        except Exception as e:
            db.rollback()
            logger.error(f"[{self.instance_id}] Batch claim error: {e}")


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
            claimed_pipe = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
            if not claimed_pipe:
                raise ValueError(f"Pipeline #{pipeline_id} not found after JIT claim.")

            with owned_pipelines_lock:
                owned_pipelines_versions[pipeline_id] = claimed_pipe.ownership_version

            logger.info(f"[{ORCHESTRATOR_INSTANCE_ID}] Atomic JIT Claim of pipeline #{pipeline_id}. Version: {claimed_pipe.ownership_version}")

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
                global coordinator
                if coordinator and coordinator.reconcile_callback:
                    coordinator.reconcile_callback(db)
            except Exception as e:
                logger.error(f"Error publishing JIT claim event or reconciling: {e}")
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