import React, { useState, useEffect } from 'react';
import { Database, Server, Cpu, Layers, Play, Zap, Shield, HelpCircle, Activity, Globe } from 'lucide-react';
import { getDatabaseStatus, getQueueStats, getWorkersRegistry, fetchVectorStats } from '../services/api';

const COMPONENT_DETAILS = {
  client: {
    title: "Client Dashboard UI",
    tech: "React 19, React Flow, Recharts, Lucide Icons",
    role: "Provides operators with visual, real-time observability over DAG executions, active workers metrics, backpressure queue depths, and sandboxed time-travel replay debugging.",
    tradeoffs: "Uses HTTP polling (3s) instead of WebSockets. Polling keeps backend architectures simpler and stateless, allowing orchestrators to crash and reboot without websocket reconnection storms."
  },
  orchestrator: {
    title: "Orchestration Runtime",
    tech: "Flask, SQLAlchemy, Python 3.11",
    role: "Coordinates pipeline execution. Heartbeats in Redis, claims/leases pipelines in PostgreSQL, tracks DAG dependency resolution, schedules unblock checks, and enforces active backpressure controls.",
    tradeoffs: "Active/Active setup. Rather than a single leader processing all pipelines, orchestrators share workload by claiming pipeline leases. A global leader election is used solely to coordinate background recovery and event compaction tasks."
  },
  redis: {
    title: "Redis Message Broker",
    tech: "Redis 7.2 (Dockerized)",
    role: "Hosts FIFO priority queues and capability-aware task buffers. Workers pop leased tasks from these queues in a Weighted Round-Robin (WRR) order to prevent priority starvation.",
    tradeoffs: "Redis is selected for its in-memory latency (<1ms) and atomic popping operations. Using PostgreSQL for queues would cause heavy row lock contention and database scaling limits."
  },
  workers: {
    title: "Worker Pool",
    tech: "Dockerized Daemon (Python 3.11), PyTorch",
    role: "Executes work. Claims task leases from capability queues, spawns lease renewal threads, processes document chunks, generates text embeddings, and communicates results through filesystem artifacts.",
    tradeoffs: "Workers are decoupled from orchestrator scheduling. They do not know about DAGs; they simply poll their capability queues. This ensures worker crashes never crash the orchestration graph state."
  },
  postgres: {
    title: "PostgreSQL Database",
    tech: "PostgreSQL 16 (Port 5433)",
    role: "Stores ACID persistent state for pipelines, tasks, worker registries, task dependencies, and the append-only event log used for deterministic state recovery.",
    tradeoffs: "Chosen for absolute transaction safety. Event-sourcing ledger updates require strict ACID guarantees. SQLite is provided as an automatic fallback for simple dev setups."
  },
  qdrant: {
    title: "Qdrant Vector Database",
    tech: "Qdrant (Dockerized), Sentence Transformers",
    role: "Manages document chunk embeddings. Indexes 384-dimensional vector coordinates, applies metadata filters by file or pipeline ID, and runs semantic search queries for retrieval pipelines.",
    tradeoffs: "Uses local docker volume persistence. Model embedding is performed on workers to offload GPU CPU constraints from the Flask orchestration api servers."
  },
  replay: {
    title: "Replay Sandbox",
    tech: "Event Sourcing Pattern, In-Memory Ledger Scrubber",
    role: "Reconstructs pipeline state at any point in history. Reads append-only postgres event logs and scrubber steps in memory. Replay never triggers side effects like Redis enqueues or worker execution.",
    tradeoffs: "Saves a snapshot every 10 events. Replays load the closest preceding snapshot and apply subsequent events, ensuring state recovery is an O(K) operation (K = snapshot window) rather than O(N) total events."
  }
};

const ArchitectureOverview = () => {
  const [selectedNode, setSelectedNode] = useState('orchestrator');
  const [isSimulating, setIsSimulating] = useState(true);
  
  // Status states
  const [dbStatus, setDbStatus] = useState('checking');
  const [redisStatus, setRedisStatus] = useState('checking');
  const [qdrantStatus, setQdrantStatus] = useState('checking');
  const [workersCount, setWorkersCount] = useState(0);

  useEffect(() => {
    const checkServices = async () => {
      // 1. Check DB
      try {
        const db = await getDatabaseStatus();
        setDbStatus(db.status === 'connected' ? 'online' : 'offline');
      } catch {
        setDbStatus('offline');
      }

      // 2. Check Redis
      try {
        await getQueueStats();
        setRedisStatus('online');
      } catch {
        setRedisStatus('offline');
      }

      // 3. Check Workers
      try {
        const workers = await getWorkersRegistry();
        setWorkersCount(workers.filter(w => w.status !== 'offline').length);
      } catch {
        setWorkersCount(0);
      }

      // 4. Check Qdrant
      try {
        const qdrant = await fetchVectorStats();
        setQdrantStatus(qdrant.status === 'ok' ? 'online' : 'offline');
      } catch {
        setQdrantStatus('offline');
      }
    };

    checkServices();
    const interval = setInterval(checkServices, 10000);
    return () => clearInterval(interval);
  }, []);

  const details = COMPONENT_DETAILS[selectedNode];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', marginTop: '10px' }}>
      
      {/* Top Banner and Simulation Control */}
      <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '4px', padding: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', boxShadow: 'none' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: '800', color: '#fff', margin: 0, display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Layers size={22} style={{ color: 'var(--color-accent)' }} />
            System Architecture Overview
          </h2>
          <p style={{ margin: '4px 0 0 0', fontSize: '0.85rem', color: '#94a3b8' }}>
            Explore the core building blocks of ScaleFlow. Click on any block in the flowchart below to inspect details.
          </p>
        </div>
        <button
          onClick={() => setIsSimulating(!isSimulating)}
          style={{
            background: isSimulating ? 'rgba(91, 140, 255, 0.1)' : 'rgba(255, 255, 255, 0.02)',
            border: isSimulating ? '1px solid rgba(91, 140, 255, 0.3)' : '1px solid var(--border-subtle)',
            borderRadius: '4px',
            padding: '8px 16px',
            fontSize: '0.85rem',
            color: isSimulating ? 'var(--color-accent)' : '#cbd5e1',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            transition: 'all 0.2s'
          }}
        >
          <Play size={16} className={isSimulating ? 'animate-spin' : ''} style={{ animationDuration: '3s' }} />
          {isSimulating ? "Pause Data Simulation" : "Animate Data Flow"}
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(12, 1fr)', gap: '24px' }}>
        
        {/* Left Column: Interactive Diagram */}
        <div style={{ gridColumn: 'span 8', background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '4px', padding: '20px', minHeight: '520px', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden', position: 'relative', boxShadow: 'none' }}>
          
          {/* Legend */}
          <div style={{ position: 'absolute', top: '16px', left: '16px', display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.75rem', color: '#94a3b8', zIndex: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--color-success)' }}></div>
              <span>Service Connected</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--color-warning)' }}></div>
              <span>Checking Connectivity</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--color-failure)' }}></div>
              <span>Service Offline</span>
            </div>
          </div>

          <svg width="100%" height="480" viewBox="0 0 800 480" style={{ maxWidth: '100%' }}>
            <defs>
              <linearGradient id="purpleGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#5B8CFF" />
                <stop offset="100%" stopColor="#3b82f6" />
              </linearGradient>
              <linearGradient id="blueGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#3b82f6" />
                <stop offset="100%" stopColor="#1d4ed8" />
              </linearGradient>
              <linearGradient id="emeraldGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#10b981" />
                <stop offset="100%" stopColor="#047857" />
              </linearGradient>
              <linearGradient id="darkGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#161d30" />
                <stop offset="100%" stopColor="#0e1322" />
              </linearGradient>
              <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#475569" />
              </marker>
            </defs>

            {/* FLOW PATHS (Dashed lines) */}
            {/* Path 1: Client to Orchestrator */}
            <path d="M 120 220 L 260 220" fill="none" stroke="#475569" strokeWidth="2" markerEnd="url(#arrow)" />
            {isSimulating && (
              <path d="M 120 220 L 260 220" fill="none" stroke="var(--color-accent)" strokeWidth="2" strokeDasharray="6 12" strokeDashoffset="0" style={{ animation: 'dash 1.5s linear infinite' }} />
            )}

            {/* Path 2: Orchestrator to Redis */}
            <path d="M 330 180 L 330 90 L 460 90" fill="none" stroke="#475569" strokeWidth="2" markerEnd="url(#arrow)" />
            {isSimulating && (
              <path d="M 330 180 L 330 90 L 460 90" fill="none" stroke="var(--color-accent)" strokeWidth="2" strokeDasharray="6 12" strokeDashoffset="0" style={{ animation: 'dash 1.5s linear infinite' }} />
            )}

            {/* Path 3: Redis to Workers */}
            <path d="M 520 120 L 520 180" fill="none" stroke="#475569" strokeWidth="2" markerEnd="url(#arrow)" />
            {isSimulating && (
              <path d="M 520 120 L 520 180" fill="none" stroke="#60a5fa" strokeWidth="2" strokeDasharray="6 12" strokeDashoffset="0" style={{ animation: 'dash 1.5s linear infinite' }} />
            )}

            {/* Path 4: Orchestrator to Postgres */}
            <path d="M 330 260 L 330 360 L 460 360" fill="none" stroke="#475569" strokeWidth="2" markerEnd="url(#arrow)" />
            {isSimulating && (
              <path d="M 330 260 L 330 360 L 460 360" fill="none" stroke="var(--color-success)" strokeWidth="2" strokeDasharray="6 12" strokeDashoffset="0" style={{ animation: 'dash 1.5s linear infinite' }} />
            )}

            {/* Path 5: Workers to Postgres (Writes) */}
            <path d="M 520 260 L 520 330" fill="none" stroke="#475569" strokeWidth="2" markerEnd="url(#arrow)" />
            {isSimulating && (
              <path d="M 520 260 L 520 330" fill="none" stroke="var(--color-success)" strokeWidth="2" strokeDasharray="6 12" strokeDashoffset="0" style={{ animation: 'dash 1.5s linear infinite' }} />
            )}

            {/* Path 6: Workers to Qdrant (Embeddings) */}
            <path d="M 580 220 L 680 220" fill="none" stroke="#475569" strokeWidth="2" markerEnd="url(#arrow)" />
            {isSimulating && (
              <path d="M 580 220 L 680 220" fill="none" stroke="#f43f5e" strokeWidth="2" strokeDasharray="6 12" strokeDashoffset="0" style={{ animation: 'dash 1.5s linear infinite' }} />
            )}

            {/* Path 7: Postgres to Replay Sandbox */}
            <path d="M 460 390 L 220 390 L 220 260" fill="none" stroke="#475569" strokeWidth="2" strokeDasharray="4 4" markerEnd="url(#arrow)" />
            {isSimulating && (
              <path d="M 460 390 L 220 390 L 220 260" fill="none" stroke="var(--color-warning)" strokeWidth="2" strokeDasharray="6 12" strokeDashoffset="0" style={{ animation: 'dash 2s linear infinite' }} />
            )}


            {/* NODES DESIGN */}
            
            {/* 1. Client Dashboard */}
            <g transform="translate(20, 180)" onClick={() => setSelectedNode('client')} style={{ cursor: 'pointer' }}>
              <rect x="0" y="0" width="100" height="80" rx="10" fill={selectedNode === 'client' ? 'url(#purpleGrad)' : 'url(#darkGrad)'} stroke={selectedNode === 'client' ? 'var(--color-accent)' : 'var(--border-subtle)'} strokeWidth="2" />
              <text x="50" y="32" fill="#fff" fontSize="12" fontWeight="bold" textAnchor="middle">Client UI</text>
              <text x="50" y="52" fill={selectedNode === 'client' ? '#e9d5ff' : '#6B7280'} fontSize="10" textAnchor="middle">React Webapp</text>
              {/* Icon */}
              <circle cx="50" cy="65" r="5" fill="var(--color-success)" />
            </g>

            {/* 2. Orchestrator */}
            <g transform="translate(260, 180)" onClick={() => setSelectedNode('orchestrator')} style={{ cursor: 'pointer' }}>
              <rect x="0" y="0" width="140" height="80" rx="10" fill={selectedNode === 'orchestrator' ? 'url(#purpleGrad)' : 'url(#darkGrad)'} stroke={selectedNode === 'orchestrator' ? 'var(--color-accent)' : 'var(--border-subtle)'} strokeWidth="2" />
              <text x="70" y="30" fill="#fff" fontSize="12" fontWeight="bold" textAnchor="middle">Orchestrator</text>
              <text x="70" y="46" fill={selectedNode === 'orchestrator' ? '#e9d5ff' : '#6B7280'} fontSize="10" textAnchor="middle">Flask Engine</text>
              {/* Leased status text */}
              <rect x="20" y="56" width="100" height="16" rx="4" fill='var(--bg-panel)' />
              <text x="70" y="68" fill="var(--color-accent)" fontSize="9" fontWeight="500" textAnchor="middle">Active/Active Leases</text>
            </g>

            {/* 3. Redis broker */}
            <g transform="translate(460, 50)" onClick={() => setSelectedNode('redis')} style={{ cursor: 'pointer' }}>
              <rect x="0" y="0" width="120" height="70" rx="10" fill={selectedNode === 'redis' ? 'url(#blueGrad)' : 'url(#darkGrad)'} stroke={selectedNode === 'redis' ? '#60a5fa' : 'var(--border-subtle)'} strokeWidth="2" strokeDasharray={redisStatus === 'offline' ? '4 4' : 'none'} />
              <text x="60" y="28" fill="#fff" fontSize="12" fontWeight="bold" textAnchor="middle">Redis Queue</text>
              <text x="60" y="44" fill={selectedNode === 'redis' ? '#93c5fd' : '#6B7280'} fontSize="10" textAnchor="middle">Message Broker</text>
              {/* Live Connectivity */}
              <circle cx="60" cy="56" r="4" fill={redisStatus === 'online' ? 'var(--color-success)' : 'var(--color-failure)'} />
            </g>

            {/* 4. Worker Pool */}
            <g transform="translate(460, 180)" onClick={() => setSelectedNode('workers')} style={{ cursor: 'pointer' }}>
              <rect x="0" y="0" width="120" height="80" rx="10" fill={selectedNode === 'workers' ? 'url(#blueGrad)' : 'url(#darkGrad)'} stroke={selectedNode === 'workers' ? '#60a5fa' : 'var(--border-subtle)'} strokeWidth="2" />
              <text x="60" y="30" fill="#fff" fontSize="12" fontWeight="bold" textAnchor="middle">Worker Cluster</text>
              <text x="60" y="46" fill={selectedNode === 'workers' ? '#93c5fd' : '#6B7280'} fontSize="10" textAnchor="middle">WRR Consumers</text>
              {/* Active workers badge */}
              <rect x="15" y="56" width="90" height="16" rx="4" fill="rgba(34, 197, 94, 0.15)" />
              <text x="60" y="68" fill="var(--color-success)" fontSize="9" fontWeight="600" textAnchor="middle">{workersCount} Active Daemon{workersCount !== 1 ? 's' : ''}</text>
            </g>

            {/* 5. PostgreSQL */}
            <g transform="translate(460, 330)" onClick={() => setSelectedNode('postgres')} style={{ cursor: 'pointer' }}>
              <rect x="0" y="0" width="120" height="80" rx="10" fill={selectedNode === 'postgres' ? 'url(#emeraldGrad)' : 'url(#darkGrad)'} stroke={selectedNode === 'postgres' ? 'var(--color-success)' : 'var(--border-subtle)'} strokeWidth="2" strokeDasharray={dbStatus === 'offline' ? '4 4' : 'none'} />
              <text x="60" y="28" fill="#fff" fontSize="12" fontWeight="bold" textAnchor="middle">PostgreSQL</text>
              <text x="60" y="44" fill={selectedNode === 'postgres' ? '#a7f3d0' : '#6B7280'} fontSize="10" textAnchor="middle">Durable Ledger</text>
              {/* Live Connectivity */}
              <circle cx="60" cy="56" r="4" fill={dbStatus === 'online' ? 'var(--color-success)' : dbStatus === 'checking' ? 'var(--color-warning)' : 'var(--color-failure)'} style={{ marginRight: '6px' }} />
              <text x="60" y="68" fill={dbStatus === 'online' ? '#a7f3d0' : '#fca5a5'} fontSize="9" textAnchor="middle">{dbStatus === 'online' ? 'ACID SQL OK' : 'No Connection'}</text>
            </g>

            {/* 6. Qdrant DB */}
            <g transform="translate(680, 185)" onClick={() => setSelectedNode('qdrant')} style={{ cursor: 'pointer' }}>
              <rect x="0" y="0" width="100" height="70" rx="10" fill={selectedNode === 'qdrant' ? 'url(#darkGrad)' : 'url(#darkGrad)'} stroke={selectedNode === 'qdrant' ? '#f43f5e' : 'var(--border-subtle)'} strokeWidth="2" strokeDasharray={qdrantStatus === 'offline' ? '4 4' : 'none'} />
              <text x="50" y="28" fill="#fff" fontSize="12" fontWeight="bold" textAnchor="middle">Qdrant DB</text>
              <text x="50" y="44" fill={selectedNode === 'qdrant' ? '#fda4af' : '#6B7280'} fontSize="10" textAnchor="middle">Vector Store</text>
              {/* Live Connectivity */}
              <circle cx="50" cy="54" r="4" fill={qdrantStatus === 'online' ? 'var(--color-success)' : 'var(--color-failure)'} />
            </g>

            {/* 7. Replay Sandbox */}
            <g transform="translate(160, 70)" onClick={() => setSelectedNode('replay')} style={{ cursor: 'pointer' }}>
              <rect x="0" y="0" width="120" height="60" rx="10" fill={selectedNode === 'replay' ? 'url(#purpleGrad)' : 'url(#darkGrad)'} stroke={selectedNode === 'replay' ? 'var(--color-warning)' : 'var(--border-subtle)'} strokeWidth="2" />
              <text x="60" y="26" fill="#fff" fontSize="12" fontWeight="bold" textAnchor="middle">Replay Sandbox</text>
              <text x="60" y="42" fill={selectedNode === 'replay' ? '#fef3c7' : '#6B7280'} fontSize="10" textAnchor="middle">State Reconstruction</text>
            </g>

          </svg>
        </div>

        {/* Right Column: Node Details Panel */}
        <div style={{ gridColumn: 'span 4', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '4px', padding: '24px', flex: 1, display: 'flex', flexDirection: 'column', gap: '16px', boxShadow: 'none' }}>
            
            {/* Title / Header */}
            <div>
              <span style={{ fontSize: '0.75rem', fontWeight: '800', color: 'var(--color-accent)', textTransform: 'uppercase', letterSpacing: '1px' }}>Component Details</span>
              <h3 style={{ fontSize: '1.25rem', fontWeight: '800', color: '#fff', margin: '4px 0 0 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
                {selectedNode === 'postgres' && <Database size={20} style={{ color: 'var(--color-success)' }} />}
                {selectedNode === 'redis' && <Zap size={20} style={{ color: '#3b82f6' }} />}
                {selectedNode === 'workers' && <Cpu size={20} style={{ color: '#60a5fa' }} />}
                {selectedNode === 'orchestrator' && <Layers size={20} style={{ color: 'var(--color-accent)' }} />}
                {selectedNode === 'client' && <Globe size={20} style={{ color: 'var(--color-success)' }} />}
                {selectedNode === 'qdrant' && <Server size={20} style={{ color: '#f43f5e' }} />}
                {selectedNode === 'replay' && <Shield size={20} style={{ color: 'var(--color-warning)' }} />}
                {details.title}
              </h3>
            </div>

            {/* Specs / Technology Stack */}
            <div>
              <strong style={{ fontSize: '0.8rem', color: '#cbd5e1', display: 'block', marginBottom: '4px' }}>Technology Stack:</strong>
              <div style={{ background: 'rgba(0, 0, 0, 0.2)', padding: '10px 14px', borderRadius: '4px', border: '1px solid var(--border-subtle)', fontSize: '0.8rem', fontFamily: 'monospace', color: 'var(--color-accent)' }}>
                {details.tech}
              </div>
            </div>

            {/* Core Responsibilities */}
            <div>
              <strong style={{ fontSize: '0.8rem', color: '#cbd5e1', display: 'block', marginBottom: '4px' }}>Core Responsibilities:</strong>
              <p style={{ margin: 0, fontSize: '0.825rem', color: '#94a3b8', lineHeight: '1.5' }}>
                {details.role}
              </p>
            </div>

            {/* Tradeoffs and System Design details */}
            <div style={{ marginTop: 'auto', borderTop: '1px solid var(--border-subtle)', paddingTop: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--color-warning)', fontSize: '0.8rem', fontWeight: 'bold', marginBottom: '6px' }}>
                <HelpCircle size={14} />
                System Design Tradeoffs
              </div>
              <p style={{ margin: 0, fontSize: '0.8rem', color: '#6B7280', lineHeight: '1.4', fontStyle: 'italic' }}>
                "{details.tradeoffs}"
              </p>
            </div>

          </div>

          {/* Quick Demo Narrative Help Card */}
          <div style={{ background: 'rgba(255, 255, 255, 0.01)', border: '1px solid var(--border-subtle)', borderRadius: '4px', padding: '16px', fontSize: '0.8rem', color: '#94a3b8' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#fff', fontWeight: 'bold', marginBottom: '6px' }}>
              <Activity size={16} style={{ color: 'var(--color-accent)' }} />
              Active System Flow Path
            </div>
            <span>
              1. **Gateway** enqueues root tasks in capability-specific queues. 
              2. **Workers** pop tasks, publish **Events**, update status, and store vectors.
              3. **Recovery** handles timeouts. **Replay Sandbox** scrubs states safely in isolation.
            </span>
          </div>

        </div>

      </div>

      {/* CSS Animation declaration */}
      <style>{`
        @keyframes dash {
          to {
            stroke-dashoffset: -120;
          }
        }
      `}</style>

    </div>
  );
};

export default ArchitectureOverview;
