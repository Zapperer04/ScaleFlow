import React from 'react';
import { 
  Upload, Cpu, Activity, RefreshCw, AlertTriangle, Shield, Play, ArrowRight, Server, Database, Search
} from 'lucide-react';

const OverviewPage = ({ 
  pipelines, 
  workers, 
  queueStats, 
  stats, 
  onSelectPipeline, 
  onNavigateToView,
  onUploadFile,
  fileType,
  setFileType,
  uploading,
  uploadStatus
}) => {
  
  const totalQueued = queueStats.total || 0;
  const maxBacklog = 50;
  const queuePressure = Math.min(100, Math.round((totalQueued / maxBacklog) * 100));
  const onlineWorkers = workers.filter(w => w.status !== 'offline');
  const topPipelines = pipelines.slice(0, 5);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      onUploadFile(file);
    }
  };

  // Get active status messages for recovery
  const getRecentRecoveryAlerts = () => {
    const alerts = [];
    const isRecovering = pipelines.some(p => p.status === 'recovering');
    const offlineCount = workers.filter(w => w.status === 'offline').length;

    if (isRecovering) {
      alerts.push("Orchestrator recovery thread is reassigning task leases.");
    }
    if (offlineCount > 0) {
      alerts.push(`${offlineCount} worker node(s) currently reporting offline.`);
    }
    if (queuePressure > 60) {
      alerts.push("Queue backpressure threshold exceeded. Low-priority tasks deferred.");
    }
    
    if (alerts.length === 0) {
      alerts.push("All lease checks reporting optimal. No active lease expirations.");
    }
    return alerts;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* 1. COMPACT CLUSTER HEALTH STRIP */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        background: 'var(--bg-panel)',
        border: '1px solid var(--border-subtle)',
        borderRadius: '6px',
        padding: '10px 16px',
        fontSize: '0.75rem',
        color: 'var(--text-muted-light)'
      }}>
        <div style={{ display: 'flex', gap: '20px' }}>
          <div>
            <span>PostgreSQL: </span>
            <span style={{ color: 'var(--color-success)', fontWeight: 'bold' }}>ONLINE</span>
          </div>
          <div style={{ borderLeft: '1px solid var(--border-subtle)', paddingLeft: '20px' }}>
            <span>Redis Broker: </span>
            <span style={{ color: 'var(--color-success)', fontWeight: 'bold' }}>ONLINE</span>
          </div>
          <div style={{ borderLeft: '1px solid var(--border-subtle)', paddingLeft: '20px' }}>
            <span>Qdrant Core: </span>
            <span style={{ color: 'var(--color-success)', fontWeight: 'bold' }}>ONLINE</span>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '16px', fontFamily: 'monospace' }}>
          <span>Workers: <strong style={{ color: '#fff' }}>{onlineWorkers.length} online</strong></span>
          <span>Queue Depth: <strong style={{ color: '#fff' }}>{totalQueued}</strong></span>
        </div>
      </div>

      {/* 2. THE CORE ORCHESTRATION lifecycle MAP */}
      <div style={{
        background: 'var(--bg-panel)',
        border: '1px solid var(--border-subtle)',
        borderRadius: '6px',
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '20px'
      }}>
        <div>
          <h3 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Platform Orchestration Flow Map
          </h3>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            The lifecycle pipeline of distributed task ingestion, execution, and replay recovery.
          </span>
        </div>

        {/* Horizontal Flow Steps Grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr auto 1.2fr auto 1.2fr auto 1.2fr auto 1fr',
          alignItems: 'start',
          gap: '12px',
          padding: '10px 0'
        }}>
          
          {/* Step 1: Upload */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{
              background: 'rgba(255, 255, 255, 0.02)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '4px',
              padding: '10px',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: '600', fontSize: '0.75rem' }}>
                <Upload size={14} style={{ color: 'var(--color-accent)' }} />
                <span>1. Upload / Ingest</span>
              </div>
              <select 
                value={fileType}
                onChange={(e) => setFileType(e.target.value)}
                style={{
                  background: '#090a0c',
                  border: '1px solid var(--border-subtle)',
                  color: '#fff',
                  fontSize: '0.7rem',
                  padding: '4px',
                  borderRadius: '4px',
                  outline: 'none',
                  width: '100%'
                }}
              >
                <option value="document_processing_demo">Doc Pipeline</option>
                <option value="log_analysis_demo">Log Pipeline</option>
              </select>
              <label style={{
                background: uploading ? 'rgba(59, 130, 246, 0.2)' : 'var(--color-accent)',
                color: '#fff',
                padding: '4px 8px',
                borderRadius: '4px',
                fontSize: '0.7rem',
                fontWeight: '600',
                cursor: uploading ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '4px'
              }}>
                {uploading ? "Ingesting..." : "Upload File"}
                <input type="file" onChange={handleFileChange} disabled={uploading} style={{ display: 'none' }} />
              </label>
            </div>
            {uploadStatus && (
              <span style={{ fontSize: '0.65rem', color: 'var(--color-success)', wordBreak: 'break-all', display: 'block', lineHeight: 1.3 }}>
                {uploadStatus}
              </span>
            )}
          </div>

          {/* Arrow */}
          <div style={{ display: 'flex', alignSelf: 'center', color: 'var(--text-muted)' }}>
            <ArrowRight size={14} />
          </div>

          {/* Step 2: Orchestration (DAG) */}
          <div style={{
            background: 'rgba(255, 255, 255, 0.02)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '4px',
            padding: '10px',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: '600', fontSize: '0.75rem' }}>
              <Cpu size={14} style={{ color: 'var(--color-accent)' }} />
              <span>2. Orchestration</span>
            </div>
            <span style={{ fontSize: '0.65rem', color: 'var(--text-muted-light)', lineHeight: 1.4 }}>
              Compiling tasks into a topologically sorted DAG with strict dependency checks.
            </span>
            <button 
              onClick={() => onNavigateToView('pipelines')}
              style={{
                background: 'var(--border-subtle)',
                border: '1px solid var(--border-subtle)',
                color: '#fff',
                padding: '4px 8px',
                borderRadius: '4px',
                fontSize: '0.7rem',
                cursor: 'pointer',
                textAlign: 'center'
              }}
            >
              Active DAGs
            </button>
          </div>

          {/* Arrow */}
          <div style={{ display: 'flex', alignSelf: 'center', color: 'var(--text-muted)' }}>
            <ArrowRight size={14} />
          </div>

          {/* Step 3: Execution */}
          <div style={{
            background: 'rgba(255, 255, 255, 0.02)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '4px',
            padding: '10px',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: '600', fontSize: '0.75rem' }}>
              <Activity size={14} style={{ color: 'var(--color-accent)' }} />
              <span>3. Execution</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem' }}>
                <span>Backpressure:</span>
                <span style={{ fontWeight: 'bold', color: queuePressure > 60 ? 'var(--color-failure)' : 'var(--color-success)' }}>
                  {queuePressure > 60 ? "Active" : "Optimal"}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem' }}>
                <span>Worker Popping:</span>
                <span style={{ fontWeight: 'bold', color: 'var(--color-success)' }}>WRR Active</span>
              </div>
            </div>
            <button 
              onClick={() => onNavigateToView('workers')}
              style={{
                background: 'var(--border-subtle)',
                border: '1px solid var(--border-subtle)',
                color: '#fff',
                padding: '4px 8px',
                borderRadius: '4px',
                fontSize: '0.7rem',
                cursor: 'pointer',
                textAlign: 'center'
              }}
            >
              Workers Registry
            </button>
          </div>

          {/* Arrow */}
          <div style={{ display: 'flex', alignSelf: 'center', color: 'var(--text-muted)' }}>
            <ArrowRight size={14} />
          </div>

          {/* Step 4: Recovery */}
          <div style={{
            background: 'rgba(255, 255, 255, 0.02)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '4px',
            padding: '10px',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: '600', fontSize: '0.75rem' }}>
              <RefreshCw size={14} style={{ color: 'var(--color-accent)' }} />
              <span>4. Recovery</span>
            </div>
            <span style={{ fontSize: '0.65rem', color: 'var(--text-muted-light)', lineHeight: 1.4, height: '32px', overflow: 'hidden' }}>
              {getRecentRecoveryAlerts()[0]}
            </span>
            <button 
              onClick={() => onNavigateToView('validation-lab')}
              style={{
                background: 'var(--border-subtle)',
                border: '1px solid var(--border-subtle)',
                color: '#fff',
                padding: '4px 8px',
                borderRadius: '4px',
                fontSize: '0.7rem',
                cursor: 'pointer',
                textAlign: 'center'
              }}
            >
              Chaos & Failover Lab
            </button>
          </div>

          {/* Arrow */}
          <div style={{ display: 'flex', alignSelf: 'center', color: 'var(--text-muted)' }}>
            <ArrowRight size={14} />
          </div>

          {/* Step 5: Replay */}
          <div style={{
            background: 'rgba(255, 255, 255, 0.02)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '4px',
            padding: '10px',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: '600', fontSize: '0.75rem' }}>
              <Shield size={14} style={{ color: 'var(--color-accent)' }} />
              <span>5. Replay Engine</span>
            </div>
            <span style={{ fontSize: '0.65rem', color: 'var(--text-muted-light)', lineHeight: 1.4 }}>
              Deterministic replaying of pipelines from event source tables.
            </span>
            <button 
              onClick={() => onNavigateToView('replay')}
              style={{
                background: 'var(--border-subtle)',
                border: '1px solid var(--border-subtle)',
                color: '#fff',
                padding: '4px 8px',
                borderRadius: '4px',
                fontSize: '0.7rem',
                cursor: 'pointer',
                textAlign: 'center'
              }}
            >
              Time Travel Scrubber
            </button>
          </div>

        </div>
      </div>

      {/* 3. METRIC HERO PANEL */}
      <div className="overview-hero">
        <div className="hero-metric-card">
          <span className="hero-metric-label">Active Workflows</span>
          <span className="hero-metric-value">
            {pipelines.filter(p => ['running', 'recovering', 'created'].includes(p.status)).length}
          </span>
        </div>
        <div className="hero-metric-card">
          <span className="hero-metric-label">Cluster Workers</span>
          <span className="hero-metric-value">{onlineWorkers.length}</span>
        </div>
        <div className="hero-metric-card">
          <span className="hero-metric-label">Backlog Size</span>
          <span className="hero-metric-value">{totalQueued}</span>
        </div>
        <div className="hero-metric-card">
          <span className="hero-metric-label">Forced Overloads</span>
          <span className="hero-metric-value">
            {pipelines.reduce((sum, p) => sum + (p.status === 'recovering' ? 1 : 0), 0)}
          </span>
        </div>
        <div className="hero-metric-card">
          <span className="hero-metric-label">Avg Execution Latency</span>
          <span className="hero-metric-value">1.82s</span>
        </div>
      </div>

      {/* 4. PIPELINE GRID & INCIDENT FEED */}
      <div className="overview-split">
        
        {/* Recent Workflows */}
        <div className="overview-pipelines-card">
          <div className="card-header-row">
            <span className="card-title">Recent Dag Ingestions</span>
            <button 
              onClick={() => onNavigateToView('pipelines')} 
              style={{ background: 'none', border: 'none', color: 'var(--color-accent)', fontSize: '0.75rem', fontWeight: '600', cursor: 'pointer' }}
            >
              View All Workflows →
            </button>
          </div>
          
          <div className="pipelines-compact-list">
            {topPipelines.length === 0 ? (
              <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', padding: '16px 0', textAlign: 'center' }}>
                No active workflows in current database. Trigger a template or upload a document to begin.
              </div>
            ) : (
              topPipelines.map((p) => {
                const totalTasks = p.tasks_count || 4;
                const completedTasks = p.completed_tasks_count || (p.status === 'completed' ? totalTasks : 0);
                const progressPct = Math.round((completedTasks / totalTasks) * 100);

                return (
                  <div key={p.id} className="pipeline-compact-item" onClick={() => onSelectPipeline(p.id)}>
                    <div className="pipeline-info">
                      <span className="pipeline-name">Pipeline #{p.id}: {p.name}</span>
                      <span className="pipeline-meta">Type: {p.pipeline_type}</span>
                    </div>
                    <div className="pipeline-progress-container">
                      <div className="progress-bar-outer">
                        <div 
                          className={`progress-bar-inner ${p.status}`} 
                          style={{ width: `${progressPct}%` }} 
                        />
                      </div>
                      <span className="progress-text">{progressPct}%</span>
                    </div>
                    <span className={`badge ${p.status}`} style={{ minWidth: '70px', textAlign: 'center', justifyContent: 'center', fontSize: '0.65rem' }}>
                      {p.status}
                    </span>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Incident Alerts Feed */}
        <div className="overview-incidents-card">
          <div className="card-header-row">
            <span className="card-title">Platform Incident Feed</span>
          </div>
          <div className="incidents-list">
            {/* Compute list based on real state */}
            {workers.filter(w => w.status === 'offline').map(w => (
              <div key={w.worker_id} className="incident-item lease">
                <div className="incident-icon">
                  <Server size={12} style={{ color: 'var(--color-replay)' }} />
                </div>
                <div className="incident-details">
                  <span className="incident-message">Worker node {w.worker_id} heartbeat lost</span>
                  <span className="incident-time">Offline</span>
                </div>
              </div>
            ))}
            
            {pipelines.some(p => p.status === 'recovering') && (
              <div className="incident-item recovery">
                <div className="incident-icon">
                  <RefreshCw size={12} style={{ color: 'var(--color-warning)' }} />
                </div>
                <div className="incident-details">
                  <span className="incident-message">Lease expiry recovery sweep in progress</span>
                  <span className="incident-time">Active</span>
                </div>
              </div>
            )}

            {queuePressure > 60 && (
              <div className="incident-item backpressure">
                <div className="incident-icon">
                  <AlertTriangle size={12} style={{ color: 'var(--color-failure)' }} />
                </div>
                <div className="incident-details">
                  <span className="incident-message">Backpressure saturated: admission throttled</span>
                  <span className="incident-time">Active</span>
                </div>
              </div>
            )}

            {workers.filter(w => w.status === 'offline').length === 0 && !pipelines.some(p => p.status === 'recovering') && queuePressure <= 60 && (
              <div className="incident-item" style={{ borderLeft: '2px solid var(--color-success)' }}>
                <div className="incident-icon">
                  <Shield size={12} style={{ color: 'var(--color-success)' }} />
                </div>
                <div className="incident-details">
                  <span className="incident-message">All cluster orchestrations healthy</span>
                  <span className="incident-time">Continuous check</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

    </div>
  );
};

export default OverviewPage;
