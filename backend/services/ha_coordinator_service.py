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
owned_pipelines_versions = {} # pipeline_id -> ownership_version (Fencing Token)
ha_thread_started = False

class HACoordinator:
    def __init__(self):
        self.instance_id = ORCHESTRATOR_INSTANCE_ID
        self.heartbeat_interval = 1.0
        self.lease_duration = 5.0 # seconds
        self.running = False
        self.leader_lock_key = "scaleflow:leader_lock"
        self.db_session = SessionLocal()
        
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
                redis_client.set(f"scaleflow:orchestrator:{self.instance_id}:heartbeat", "alive", ex=int(self.lease_duration))
                
                # 3. Leader Election try
                # Set NX EX
                acquired = redis_client.set(self.leader_lock_key, self.instance_id, nx=True, ex=int(self.lease_duration))
                if acquired:
                    is_leader_instance = True
                else:
                    # Check if already leader, extend lease
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
            time.sleep(2.0)

    def _renew_owned_pipelines(self, db):
        global owned_pipelines_versions
        pids = list(owned_pipelines_versions.keys())
        now = datetime.now()
        new_expiry = now + timedelta(seconds=30)
        
        for pid in pids:
            try:
                # Check if we still hold the ownership in DB
                pipe = db.query(Pipeline).filter(Pipeline.id == pid).first()
                if pipe and pipe.owner_instance_id == self.instance_id and pipe.owner_lease_expires_at is not None and pipe.owner_lease_expires_at > now:
                    # Renew lease in DB
                    pipe.owner_lease_expires_at = new_expiry
                    db.commit()
                else:
                    # We lost the lease or someone else took it
                    print(f"[{self.instance_id}] Lost lease ownership of pipeline #{pid}", flush=True)
                    owned_pipelines_versions.pop(pid, None)
            except Exception as e:
                db.rollback()
                print(f"[{self.instance_id}] Error renewing lease for pipeline #{pid}: {e}", flush=True)

    def _claim_active_pipelines(self, db):
        global owned_pipelines_versions
        now = datetime.now()
        new_expiry = now + timedelta(seconds=30)
        
        # Query pipelines that are running/recovering and either unowned or lease expired
        active_pipes = db.query(Pipeline).filter(
            Pipeline.status.in_(['running', 'recovering', 'created']),
            (Pipeline.owner_instance_id == None) | (Pipeline.owner_lease_expires_at == None) | (Pipeline.owner_lease_expires_at < now)
        ).all()
        
        for pipe in active_pipes:
            # Skip if we already think we own it but lease expired (we will renew or reclaim it here)
            # Try to claim atomically using update
            try:
                stmt = text(
                    "UPDATE pipelines "
                    "SET owner_instance_id = :my_id, owner_lease_expires_at = :expiry, ownership_version = ownership_version + 1 "
                    "WHERE id = :pid AND (owner_instance_id IS NULL OR owner_lease_expires_at IS NULL OR owner_lease_expires_at < :now OR owner_instance_id = :my_id)"
                )
                res = db.execute(stmt, {
                    "my_id": self.instance_id,
                    "expiry": new_expiry,
                    "now": now,
                    "pid": pipe.id
                })
                db.commit()
                
                # Check if update succeeded (rowcount > 0)
                if res.rowcount > 0:
                    # Fetch latest version to use as fencing token
                    db.refresh(pipe)
                    owned_pipelines_versions[pipe.id] = pipe.ownership_version
                    print(f"[{self.instance_id}] Claimed/Takeover pipeline #{pipe.id} successfully. Version token: {pipe.ownership_version}", flush=True)
                    
                    # Log event sourcing takeover event
                    from services.event_sourcing_service import publish_event
                    publish_event(
                        db=db,
                        event_type="PIPELINE_OWNERSHIP_TAKEN_OVER", # We will allow it in validation mapping
                        pipeline_id=pipe.id,
                        message=f"Orchestrator {self.instance_id} assumed ownership.",
                        worker_id=self.instance_id,
                        payload={"instance_id": self.instance_id, "ownership_version": pipe.ownership_version}
                    )
                    db.commit()
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
    
    # Check database directly
    pipe = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
    if not pipe:
        raise ValueError(f"Pipeline #{pipeline_id} not found.")
        
    now = datetime.now()
    
    # 1. JIT Claim if unowned or lease has expired
    if pipe.owner_instance_id is None or pipe.owner_lease_expires_at is None or pipe.owner_lease_expires_at < now:
        new_expiry = now + timedelta(seconds=30)
        stmt = text(
            "UPDATE pipelines "
            "SET owner_instance_id = :my_id, owner_lease_expires_at = :expiry, ownership_version = ownership_version + 1 "
            "WHERE id = :pid AND (owner_instance_id IS NULL OR owner_lease_expires_at IS NULL OR owner_lease_expires_at < :now)"
        )
        res = db.execute(stmt, {
            "my_id": ORCHESTRATOR_INSTANCE_ID,
            "expiry": new_expiry,
            "now": now,
            "pid": pipeline_id
        })
        db.commit()
        if res.rowcount > 0:
            db.refresh(pipe)
            owned_pipelines_versions[pipeline_id] = pipe.ownership_version
            print(f"[{ORCHESTRATOR_INSTANCE_ID}] Atomic JIT Claim of pipeline #{pipeline_id} successfully. Version: {pipe.ownership_version}", flush=True)
            
            # Log event sourcing takeover event
            from services.event_sourcing_service import publish_event
            try:
                publish_event(
                    db=db,
                    event_type="PIPELINE_OWNERSHIP_TAKEN_OVER",
                    pipeline_id=pipeline_id,
                    message=f"Orchestrator {ORCHESTRATOR_INSTANCE_ID} JIT claimed ownership.",
                    worker_id=ORCHESTRATOR_INSTANCE_ID,
                    payload={"instance_id": ORCHESTRATOR_INSTANCE_ID, "ownership_version": pipe.ownership_version}
                )
                db.commit()
            except Exception as e:
                print(f"Error publishing JIT claim event: {e}", flush=True)
            return True

    # 2. Verify local cache/db ownership matching
    if pipe.owner_instance_id != ORCHESTRATOR_INSTANCE_ID:
        raise ValueError(f"Fencing conflict: Orchestrator {ORCHESTRATOR_INSTANCE_ID} does not own pipeline #{pipeline_id}.")
        
    if pipeline_id not in owned_pipelines_versions:
        raise ValueError(f"Fencing conflict: Orchestrator {ORCHESTRATOR_INSTANCE_ID} does not own pipeline #{pipeline_id} locally.")
        
    local_ver = owned_pipelines_versions[pipeline_id]
    if pipe.ownership_version != local_ver:
        # We lost it! Evict from cache
        owned_pipelines_versions.pop(pipeline_id, None)
        raise ValueError(
            f"Fencing conflict: pipeline #{pipeline_id} ownership version mismatch! "
            f"Local token: {local_ver}, DB token: {pipe.ownership_version}. Takeover detected."
        )
    return True

# Singleton instance
coordinator = HACoordinator()
