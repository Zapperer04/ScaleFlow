import React from 'react';
import { Server } from 'lucide-react';

const WorkerStatus = ({ workers }) => {
  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Active Workers</h2>
        <span className="panel-subtitle">Live worker health status</span>
      </div>
      <div className="workers-list">
        {workers.length === 0 ? (
          <div className="empty-log">
            <Server size={32} opacity={0.3} />
            <p>No workers connected</p>
          </div>
        ) : (
          workers.map((worker, idx) => (
            <div key={idx} className="worker-item">
              <div className="worker-indicator active" />
              <div className="worker-info">
                <div className="worker-name">{worker.worker_id}</div>
                <div className="worker-status">
                  Last seen: {new Date(worker.last_seen).toLocaleTimeString()}
                </div>
                <div className="worker-stats" style={{marginTop: '4px', fontSize: '0.8rem', display: 'flex', gap: '8px', color: '#9ca3af'}}>
                  <span className={`worker-badge ${worker.status}`} style={{
                    padding: '2px 6px', borderRadius: '4px', background: worker.status === 'busy' ? 'rgba(59,130,246,0.2)' : 'rgba(156,163,175,0.2)'
                  }}>{worker.status}</span>
                  <span>✓ {worker.tasks_completed || 0}</span>
                  <span>✗ {worker.tasks_failed || 0}</span>
                  {worker.current_task_id && <span>Task #{worker.current_task_id}</span>}
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
