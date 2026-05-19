import React from 'react';
import { Server, Clock, Cpu, TrendingUp } from 'lucide-react';

const TaskLog = ({ tasks, onTaskClick }) => {
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
          tasks.map((task) => (
            <div key={task.id} className={`log-entry status-${task.status} clickable`} onClick={() => onTaskClick && onTaskClick(task.id)}>
              <div className="log-header">
                <div className="log-id">
                  <div className="status-indicator" />
                  <span>#{task.id}</span>
                </div>
                <div className="log-badge">
                  {task.status}
                  {task.retry_count > 0 && ` (Retry ${task.retry_count}/${task.max_retries})`}
                </div>
              </div>
              <div className="log-body">
                <code className="log-type">{task.type}</code>
                <span className={`priority-badge priority-${task.priority}`}>
                  {task.priority}
                </span>
                <span className="log-data">{JSON.stringify(task.data)}</span>
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
          ))
        )}
      </div>
    </div>
  );
};

export default TaskLog;
