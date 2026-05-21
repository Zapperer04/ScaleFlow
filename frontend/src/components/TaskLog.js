import React from 'react';
import { Server, Clock, Cpu, TrendingUp, AlertTriangle } from 'lucide-react';

const TaskLog = ({ tasks, workers, onTaskClick, page, totalPages, onPageChange }) => {
  const activeWorkersExist = workers && workers.some(w => w.status !== 'offline');

  const getPendingDuration = (createdAtStr) => {
    const diffMs = Date.now() - new Date(createdAtStr);
    const diffSec = Math.max(0, Math.floor(diffMs / 1000));
    if (diffSec < 60) return `${diffSec}s`;
    const diffMin = Math.floor(diffSec / 60);
    return `${diffMin}m ${diffSec % 60}s`;
  };

  const isStuck = (task) => {
    if (task.status !== 'pending') return false;
    const diffMs = Date.now() - new Date(task.created_at);
    return activeWorkersExist && diffMs > 30000;
  };

  return (
    <div className="panel execution-log">
      <div className="panel-header">
        <h2>Execution Log</h2>
        <span className="panel-subtitle">Real-time task lifecycle</span>
      </div>
      <div className="log-container">
        {tasks.length === 0 ? (
          <div className="empty-log">
            <Server size={48} opacity={0.3} />
            <p>No tasks in execution history</p>
          </div>
        ) : (
          tasks.map((task) => {
            const stuck = isStuck(task);
            return (
              <div key={task.id} className={`log-entry status-${task.status} ${stuck ? 'stuck-warning' : ''} clickable`} onClick={() => onTaskClick && onTaskClick(task.id)}>
                <div className="log-header">
                  <div className="log-id">
                    <div className="status-indicator" />
                    <span>#{task.id}</span>
                  </div>
                  <div className="log-badges">
                    <span className={`log-badge status-${task.status}`}>
                      {task.status}
                      {task.retry_count > 0 && ` (Retry ${task.retry_count}/${task.max_retries})`}
                    </span>
                    {stuck && (
                      <span className="stuck-badge">
                        <AlertTriangle size={12} />
                        Possible Stuck
                      </span>
                    )}
                  </div>
                </div>
                <div className="log-body">
                  <code className="log-type">{task.type}</code>
                  <span className={`priority-badge priority-${task.priority}`}>
                    {task.priority}
                  </span>
                  <span className="log-data">{JSON.stringify(task.data)}</span>
                  
                  {task.status === 'pending' && (
                    <div className="pending-details">
                      {!task.queued_in_redis && (
                        <div className="stale-warning-text">
                          <AlertTriangle size={14} />
                          <span>Pending in database but not found in Redis queue. Cancel or requeue this task.</span>
                        </div>
                      )}
                      <div className="pending-detail-row">
                        <span className="detail-label">Queued in Redis:</span>
                        <span className={`detail-val ${task.queued_in_redis ? 'yes' : 'no'}`}>
                          {task.queued_in_redis ? 'Yes' : 'No'}
                        </span>
                      </div>
                      {task.queued_in_redis && (
                        <>
                          <div className="pending-detail-row">
                            <span className="detail-label">Queue Name:</span>
                            <span className="detail-val code">{task.queue_name}</span>
                          </div>
                          {task.queue_position !== undefined && task.queue_position !== null && (
                            <div className="pending-detail-row">
                              <span className="detail-label">Queue Position:</span>
                              <span className="detail-val highlight">{task.queue_position}</span>
                            </div>
                          )}
                        </>
                      )}
                      <div className="pending-detail-row">
                        <span className="detail-label">Pending For:</span>
                        <span className="detail-val duration">{getPendingDuration(task.created_at)}</span>
                      </div>
                    </div>
                  )}

                  {task.dependencies && task.dependencies.length > 0 && (
                    <span className="task-deps">
                      Depends on: {task.dependencies.join(', ')}
                    </span>
                  )}
                  {task.error_message && (
                    <span className="task-error">
                      Error: {task.error_message}
                    </span>
                  )}
                </div>
                <div className="log-timeline">
                  <div className="timeline-event">
                    <Clock size={12} />
                    <span>{new Date(task.created_at).toLocaleTimeString()}</span>
                  </div>
                  {task.started_at && (
                    <div className="timeline-event">
                      <Cpu size={12} />
                      <span>{new Date(task.started_at).toLocaleTimeString()}</span>
                    </div>
                  )}
                  {task.completed_at && (
                    <div className="timeline-event">
                      <TrendingUp size={12} />
                      <span>{new Date(task.completed_at).toLocaleTimeString()}</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {totalPages > 1 && (
        <div className="pagination-controls">
          <button 
            className="pagination-btn"
            disabled={page === 1} 
            onClick={() => onPageChange(page - 1)}
          >
            &larr; Previous
          </button>
          <span className="pagination-info">
            Page {page} of {totalPages}
          </span>
          <button 
            className="pagination-btn"
            disabled={page === totalPages} 
            onClick={() => onPageChange(page + 1)}
          >
            Next &rarr;
          </button>
        </div>
      )}
    </div>
  );
};

export default TaskLog;
