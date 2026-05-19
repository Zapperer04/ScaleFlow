import React from 'react';
import { Server, CheckCircle, XCircle, Play, Eye } from 'lucide-react';

const WorkerStatus = ({ workers }) => {
  const getRelativeTime = (isoString) => {
    if (!isoString) return 'Never';
    const diffMs = Date.now() - new Date(isoString);
    const diffSec = Math.max(0, Math.floor(diffMs / 1000));
    if (diffSec < 5) return 'just now';
    if (diffSec < 60) return `${diffSec}s ago`;
    const diffMin = Math.floor(diffSec / 60);
    return `${diffMin}m ago`;
  };

  return (
    <div className="panel worker-status-panel">
      <div className="panel-header">
        <h2>Active Workers</h2>
        <span className="panel-subtitle">Live health and telemetry</span>
      </div>
      <div className="workers-list">
        {workers.length === 0 ? (
          <div className="empty-log">
            <Server size={32} opacity={0.3} />
            <p>No workers configured</p>
          </div>
        ) : (
          workers.map((worker, idx) => (
            <div key={idx} className={`worker-item status-${worker.status}`}>
              <div className="worker-header">
                <div className="worker-title">
                  <div className={`worker-indicator ${worker.status}`} />
                  <span className="worker-name">{worker.worker_id}</span>
                </div>
                <span className={`status-badge ${worker.status}`}>{worker.status}</span>
              </div>
              
              <div className="worker-body">
                <div className="worker-meta">
                  <span className="meta-label">Last seen:</span>
                  <span className="meta-val">{getRelativeTime(worker.last_seen)}</span>
                </div>
                <div className="worker-meta">
                  <span className="meta-label">Last Action:</span>
                  <span className="meta-val action-text">{worker.last_action || 'None'}</span>
                </div>
                {worker.current_task_id && (
                  <div className="worker-meta current-task">
                    <span className="meta-label">Current Task:</span>
                    <span className="meta-val highlight">#{worker.current_task_id}</span>
                  </div>
                )}
              </div>

              <div className="worker-counters">
                <div className="counter-item success">
                  <CheckCircle size={14} />
                  <span>{worker.tasks_completed || 0} completed</span>
                </div>
                <div className="counter-item danger">
                  <XCircle size={14} />
                  <span>{worker.tasks_failed || 0} failed</span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default WorkerStatus;
