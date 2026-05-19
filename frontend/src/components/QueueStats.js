import React from 'react';
import { Layers } from 'lucide-react';

const QueueStats = ({ stats }) => {
  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Redis Queues</h2>
        <span className="panel-subtitle">Live queue depths</span>
      </div>
      <div className="queue-stats-grid">
        <div className="queue-stat-card high">
          <div className="queue-label">High Priority</div>
          <div className="queue-val">{stats.high || 0}</div>
        </div>
        <div className="queue-stat-card medium">
          <div className="queue-label">Medium Priority</div>
          <div className="queue-val">{stats.medium || 0}</div>
        </div>
        <div className="queue-stat-card low">
          <div className="queue-label">Low Priority</div>
          <div className="queue-val">{stats.low || 0}</div>
        </div>
        <div className="queue-stat-card total">
          <div className="queue-label">Total Queued</div>
          <div className="queue-val">{stats.total || 0}</div>
        </div>
      </div>
    </div>
  );
};

export default QueueStats;
