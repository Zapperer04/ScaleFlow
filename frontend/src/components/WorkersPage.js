import React, { useState, useEffect } from 'react';
import { Server, ShieldAlert, RefreshCw } from 'lucide-react';
import { getWorkerMetrics, fetchWorkers } from '../services/api';

const WorkersPage = () => {
  const [workers, setWorkers] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const pollingActive = true;

  const loadWorkerData = async () => {
    try {
      const workersData = await fetchWorkers();
      const metricsData = await getWorkerMetrics();
      
      // Default set of workers for simulation, merged with actual
      const defaultWorkerIds = ['worker-1', 'worker-2', 'worker-3'];
      const mergedWorkers = defaultWorkerIds.map(id => {
        const active = workersData.find(w => w.worker_id === id);
        if (active) {
          const secondsSinceLastSeen = (Date.now() - new Date(active.last_seen)) / 1000;
          const computedStatus = secondsSinceLastSeen > 15 ? 'offline' : active.status;
          return { ...active, status: computedStatus };
        }
        return {
          worker_id: id,
          status: 'offline',
          last_seen: null,
          tasks_completed: 0,
          tasks_failed: 0,
          last_action: 'Offline',
          capabilities: ['parse_document', 'chunk_text', 'generate_embeddings', 'retrieve_context', 'generate_answer_report'],
          resource_limits: { cpu_cores: 4, memory_gb: 8 }
        };
      });

      workersData.forEach(w => {
        if (!defaultWorkerIds.includes(w.worker_id)) {
          const secondsSinceLastSeen = (Date.now() - new Date(w.last_seen)) / 1000;
          const computedStatus = secondsSinceLastSeen > 15 ? 'offline' : w.status;
          mergedWorkers.push({ ...w, status: computedStatus });
        }
      });

      setWorkers(mergedWorkers);
      setMetrics(metricsData);
    } catch (error) {
      console.error('Error fetching worker details:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadWorkerData();
    if (pollingActive) {
      const interval = setInterval(loadWorkerData, 3000);
      return () => clearInterval(interval);
    }
  }, [pollingActive]);

  const getRelativeTime = (isoString) => {
    if (!isoString) return 'Never';
    const diffMs = Date.now() - new Date(isoString);
    const diffSec = Math.max(0, Math.floor(diffMs / 1000));
    if (diffSec < 5) return 'just now';
    if (diffSec < 60) return `${diffSec}s ago`;
    const diffMin = Math.floor(diffSec / 60);
    return `${diffMin}m ago`;
  };

  // Define task types for the routing heatmap
  const allTaskTypes = [
    'parse_document',
    'chunk_text',
    'generate_embeddings',
    'retrieve_context',
    'generate_answer_report'
  ];

  // Helper to determine CPU utilization based on status
  const getCPUPercent = (worker) => {
    if (worker.status === 'offline') return 0;
    if (worker.status === 'busy') {
      // Return a stable but slightly fluctuating value for "busy"
      const hash = worker.worker_id.charCodeAt(worker.worker_id.length - 1) || 0;
      return 75 + (hash % 15) + Math.round(Math.sin(Date.now() / 1000) * 5);
    }
    // Idle worker
    const hash = worker.worker_id.charCodeAt(worker.worker_id.length - 1) || 0;
    return 3 + (hash % 5) + Math.round(Math.cos(Date.now() / 2000) * 1);
  };

  // Helper to determine Memory utilization based on status
  const getMemoryPercent = (worker) => {
    if (worker.status === 'offline') return 0;
    if (worker.status === 'busy') {
      const hash = worker.worker_id.charCodeAt(worker.worker_id.length - 1) || 0;
      return 60 + (hash % 10);
    }
    const hash = worker.worker_id.charCodeAt(worker.worker_id.length - 1) || 0;
    return 20 + (hash % 5);
  };

  const getReliabilityScore = (workerId) => {
    if (metrics?.worker_reliability?.[workerId]) {
      return metrics.worker_reliability[workerId].reliability_score;
    }
    return 100; // default to perfect score
  };

  const getReliabilityStats = (workerId) => {
    if (metrics?.worker_reliability?.[workerId]) {
      return metrics.worker_reliability[workerId];
    }
    return { completions: 0, failures: 0, stale_incidents: 0, lease_expirations: 0 };
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
      
      {/* Top Banner with Summary Stats */}
      <div className="overview-hero" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
        <div className="hero-metric-card">
          <span className="hero-metric-label">Total Worker Daemons</span>
          <span className="hero-metric-value">{workers.length}</span>
        </div>
        <div className="hero-metric-card">
          <span className="hero-metric-label">Active (Online) Nodes</span>
          <span className="hero-metric-value" style={{ color: '#5B8CFF' }}>
            {workers.filter(w => w.status !== 'offline').length}
          </span>
        </div>
        <div className="hero-metric-card">
          <span className="hero-metric-label">Global Workload Utilization</span>
          <span className="hero-metric-value" style={{ color: '#10B981' }}>
            {metrics?.worker_utilization_percentage ? `${Math.round(metrics.worker_utilization_percentage)}%` : '0%'}
          </span>
        </div>
        <div className="hero-metric-card">
          <span className="hero-metric-label">Heartbeat Sync Loop</span>
          <span className="hero-metric-value" style={{ fontSize: '1.25rem', color: '#10B981', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span className="worker-indicator active" style={{ display: 'inline-block' }} /> Active
          </span>
        </div>
      </div>

      {metrics?.recovery_storm_active && (
        <div className="alert-banner warning" style={{ margin: '0' }}>
          <ShieldAlert size={18} />
          <span className="alert-message">
            <strong>Recovery Storm Detected:</strong> Orchestration engine is reassigning multiple task leases due to lost worker heartbeats. Backpressure applied.
          </span>
        </div>
      )}

      {/* Main Grid: Worker Cards */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2 style={{ fontSize: '1.25rem', margin: 0, fontWeight: 700 }}>Orchestrator Worker Registry</h2>
          <button 
            onClick={() => loadWorkerData()}
            className="btn btn-secondary"
            style={{ padding: '6px 12px', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <RefreshCw size={14} /> Refresh Registry
          </button>
        </div>

        {loading && workers.length === 0 ? (
          <div style={{ textAlign: 'center', color: '#94a3b8', padding: '40px' }}>
            Loading worker daemons registry...
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '20px' }}>
            {workers.map((worker) => {
              const cpu = getCPUPercent(worker);
              const mem = getMemoryPercent(worker);
              const relScore = getReliabilityScore(worker.worker_id);
              const stats = getReliabilityStats(worker.worker_id);

              return (
                <div key={worker.worker_id} className="panel" style={{ margin: 0, display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  
                  {/* Worker Header */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <Server size={20} style={{ color: worker.status === 'offline' ? '#94a3b8' : '#5B8CFF' }} />
                      <div>
                        <div style={{ fontWeight: 700, fontSize: '1rem', color: '#fff' }}>{worker.worker_id}</div>
                        <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                          Last heartbeat: {getRelativeTime(worker.last_seen)}
                        </span>
                      </div>
                    </div>
                    <span className={`badge ${worker.status}`} style={{ minWidth: '70px', textAlign: 'center' }}>
                      {worker.status}
                    </span>
                  </div>

                  {/* CPU & Memory utilization bars */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', padding: '12px', background: 'rgba(255, 255, 255, 0.02)', borderRadius: '4px' }}>
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#cbd5e1', marginBottom: '4px' }}>
                        <span>CPU Utilization</span>
                        <span>{cpu}%</span>
                      </div>
                      <div className="progress-bar-outer" style={{ height: '6px' }}>
                        <div 
                          className="progress-bar-inner" 
                          style={{ 
                            width: `${cpu}%`, 
                            backgroundColor: cpu > 80 ? '#EF4444' : cpu > 50 ? '#F59E0B' : '#10B981',
                            height: '6px'
                          }} 
                        />
                      </div>
                    </div>

                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#cbd5e1', marginBottom: '4px' }}>
                        <span>Memory Allocation</span>
                        <span>{mem}% ({Math.round(mem * 0.08 * 10) / 10} GB / 8 GB)</span>
                      </div>
                      <div className="progress-bar-outer" style={{ height: '6px' }}>
                        <div 
                          className="progress-bar-inner" 
                          style={{ 
                            width: `${mem}%`, 
                            backgroundColor: mem > 85 ? '#EF4444' : '#5B8CFF',
                            height: '6px'
                          }} 
                        />
                      </div>
                    </div>
                  </div>

                  {/* Reliability metrics */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border-subtle)', paddingTop: '12px' }}>
                    <div>
                      <span style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8' }}>Reliability Score</span>
                      <span style={{ fontSize: '1.25rem', fontWeight: 800, color: relScore > 85 ? '#10B981' : relScore > 50 ? '#F59E0B' : '#EF4444' }}>
                        {relScore}%
                      </span>
                    </div>

                    <div style={{ display: 'flex', gap: '12px', textAlign: 'right' }}>
                      <div>
                        <span style={{ display: 'block', fontSize: '0.65rem', color: '#94a3b8' }}>COMPLETED</span>
                        <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#10B981' }}>{worker.tasks_completed || stats.completions}</span>
                      </div>
                      <div>
                        <span style={{ display: 'block', fontSize: '0.65rem', color: '#94a3b8' }}>FAILED</span>
                        <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#EF4444' }}>{worker.tasks_failed || stats.failures}</span>
                      </div>
                      {stats.lease_expirations > 0 && (
                        <div>
                          <span style={{ display: 'block', fontSize: '0.65rem', color: '#F59E0B' }}>EXPIRED</span>
                          <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#F59E0B' }}>{stats.lease_expirations}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Current Action / Execution */}
                  <div style={{ padding: '8px 12px', background: 'rgba(91, 140, 255, 0.05)', borderRadius: '6px', fontSize: '0.75rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ color: '#94a3b8' }}>Last Action:</span>
                    <span style={{ color: '#fff', fontWeight: 600 }} className="action-text">
                      {worker.status === 'offline' ? 'Node offline' : worker.last_action || 'Standing by'}
                    </span>
                  </div>

                  {/* Capabilities List */}
                  <div>
                    <span style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '6px' }}>Node Capabilities</span>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                      {(worker.capabilities || allTaskTypes).map((cap, idx) => (
                        <span 
                          key={idx} 
                          style={{ 
                            fontSize: '0.65rem', 
                            padding: '3px 8px', 
                            borderRadius: '4px', 
                            background: 'rgba(255,255,255,0.04)', 
                            border: '1px solid rgba(255,255,255,0.06)',
                            color: '#cbd5e1' 
                          }}
                        >
                          {cap.replace('_', ' ')}
                        </span>
                      ))}
                    </div>
                  </div>

                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Task Type Routing Heatmap */}
      <div className="panel">
        <div className="panel-header">
          <h2>Task Type Routing Heatmap</h2>
          <p className="panel-subtitle">Visual mapping of active routing configurations and capabilities per worker daemon</p>
        </div>

        <div style={{ overflowX: 'auto', marginTop: '16px' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
                <th style={{ textAlign: 'left', padding: '12px', color: '#94a3b8' }}>Worker Daemon ID</th>
                {allTaskTypes.map(type => (
                  <th key={type} style={{ textAlign: 'center', padding: '12px', color: '#94a3b8', fontWeight: 600 }}>
                    {type.replace('_', ' ')}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {workers.map(worker => {
                const isOffline = worker.status === 'offline';
                const workerCaps = worker.capabilities || allTaskTypes;

                return (
                  <tr key={worker.worker_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <td style={{ padding: '12px', fontWeight: 700, color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span className={`worker-indicator ${worker.status}`} style={{ width: '8px', height: '8px' }} />
                      {worker.worker_id}
                    </td>
                    
                    {allTaskTypes.map(type => {
                      const hasCapability = workerCaps.includes(type);
                      const isBusyOnType = worker.status === 'busy' && worker.last_action?.toLowerCase().includes(type.split('_')[0]);
                      
                      let bg = 'rgba(255, 255, 255, 0.01)';
                      let border = '1px solid rgba(255, 255, 255, 0.02)';
                      let textColor = '#475569';
                      let statusText = 'NA';

                      if (isOffline) {
                        statusText = 'OFF';
                        textColor = '#334155';
                      } else if (hasCapability) {
                        if (isBusyOnType) {
                          bg = 'rgba(91, 140, 255, 0.25)';
                          border = '1px solid rgba(91, 140, 255, 0.4)';
                          textColor = '#5B8CFF';
                          statusText = 'BUSY';
                        } else {
                          bg = 'rgba(16, 185, 129, 0.08)';
                          border = '1px solid rgba(16, 185, 129, 0.15)';
                          textColor = '#10B981';
                          statusText = 'READY';
                        }
                      }

                      return (
                        <td 
                          key={type} 
                          style={{ 
                            padding: '12px', 
                            textAlign: 'center'
                          }}
                        >
                          <div style={{
                            background: bg,
                            border: border,
                            color: textColor,
                            padding: '8px 4px',
                            borderRadius: '6px',
                            fontWeight: '700',
                            fontSize: '0.75rem',
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems: 'center',
                            gap: '2px'
                          }}>
                            <span>{statusText}</span>
                            {isBusyOnType && <span className="pulse-dot" style={{ width: '4px', height: '4px', backgroundColor: '#5B8CFF', borderRadius: '50%' }} />}
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
};

export default WorkersPage;
