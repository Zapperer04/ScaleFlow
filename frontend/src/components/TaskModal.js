import React, { useState, useEffect } from 'react';
import { X, RefreshCw, XCircle, AlertCircle } from 'lucide-react';
import { getTaskDetails, retryTask, cancelTask } from '../services/api';
import { formatTimeIST } from '../utils/timeUtils';

const TaskModal = ({ taskId, onClose, onActionComplete }) => {
  const [details, setDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchDetails = async () => {
    try {
      setLoading(true);
      const data = await getTaskDetails(taskId);
      setDetails(data);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to load details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (taskId) {
      fetchDetails();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskId]);

  if (!taskId) return null;

  const handleRetry = async () => {
    try {
      const force = details.retry_count >= details.max_retries;
      await retryTask(taskId, force);
      if (onActionComplete) onActionComplete();
      fetchDetails();
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to retry');
    }
  };

  const handleCancel = async () => {
    try {
      await cancelTask(taskId);
      if (onActionComplete) onActionComplete();
      fetchDetails();
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to cancel');
    }
  };

  const isStalePending = details && details.status === 'pending' && !details.queued_in_redis;
  const canRetry = details && ['failed', 'timed_out', 'cancelled'].includes(details.status);
  const canCancel = details && ['pending', 'queued', 'running'].includes(details.status);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Task #{taskId} Details</h2>
          <button className="close-btn" onClick={onClose}><X size={24} /></button>
        </div>
        
        {loading ? (
          <div className="modal-body"><p>Loading...</p></div>
        ) : error && !details ? (
          <div className="modal-body"><p style={{color: '#ef4444'}}>{error}</p></div>
        ) : (
          <div className="modal-body">
            {error && <div className="error-banner">{error}</div>}
            
            {isStalePending && (
              <div className="stale-warning-notice">
                <AlertCircle size={18} />
                <span>Pending in database but not found in Redis queue. Cancel or requeue this task.</span>
              </div>
            )}
            
            <div className="detail-grid">
              <div className="detail-item">
                <label>Status</label>
                <span className={`status-badge status-${details.status}`}>{details.status}</span>
              </div>
              <div className="detail-item">
                <label>Type</label>
                <code>{details.type}</code>
              </div>
              <div className="detail-item">
                <label>Priority</label>
                <span className={`priority-badge priority-${details.priority}`}>{details.priority}</span>
              </div>
              <div className="detail-item">
                <label>Retries</label>
                <span>{details.retry_count} / {details.max_retries}</span>
              </div>
              <div className="detail-item">
                <label>Worker</label>
                <span>{details.worker_id || 'None'}</span>
              </div>
              <div className="detail-item">
                <label>Dependencies</label>
                <span>{details.dependencies.length > 0 ? details.dependencies.join(', ') : 'None'}</span>
              </div>
              {details.recovered_count !== undefined && (
                <div className="detail-item">
                  <label>Recovered Count</label>
                  <span>{details.recovered_count}</span>
                </div>
              )}
              {details.assigned_worker_id && (
                <div className="detail-item">
                  <label>Assigned Worker ID</label>
                  <span style={{ fontFamily: 'monospace', color: '#3b82f6' }}>{details.assigned_worker_id}</span>
                </div>
              )}
              {details.lease_expires_at && (
                <>
                  <div className="detail-item">
                    <label>Lease Expiry</label>
                    <span>{new Date(details.lease_expires_at).toLocaleString([], { hour12: false, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
                  </div>
                  <div className="detail-item">
                    <label>Lease Remaining</label>
                    <span>
                      {(() => {
                        const remaining = Math.max(0, Math.floor((new Date(details.lease_expires_at) - Date.now()) / 1000));
                        const expiresSoon = remaining <= 10;
                        return (
                          <span style={{ color: expiresSoon ? '#ef4444' : '#10b981', fontWeight: expiresSoon ? 'bold' : 'normal' }}>
                            {remaining}s {expiresSoon && ' (Expires Soon!)'}
                          </span>
                        );
                      })()}
                    </span>
                  </div>
                </>
              )}
            </div>

            <div className="detail-section">
              <h3>Payload</h3>
              <pre className="payload-box">{JSON.stringify(details.data, null, 2)}</pre>
            </div>

            {details.error_message && (
              <div className="detail-section error-section">
                <h3><AlertCircle size={16} /> Error Message</h3>
                <p>{details.error_message}</p>
              </div>
            )}

            <div className="detail-section">
              <h3>Execution Logs</h3>
              <div className="logs-timeline">
                {details.logs && details.logs.length > 0 ? (
                  details.logs.map((log) => (
                    <div key={log.id} className="log-row">
                      <div className="log-time">{formatTimeIST(log.created_at)}</div>
                      <div className="log-type-badge">{log.event_type}</div>
                      <div className="log-msg">
                        {log.message}
                        {log.worker_id && <span className="log-worker">[{log.worker_id}]</span>}
                      </div>
                    </div>
                  ))
                ) : (
                  <p>No logs available.</p>
                )}
              </div>
            </div>
            
            <div className="modal-actions">
              {isStalePending && (
                <button className="action-btn retry-btn" onClick={handleRetry}>
                  <RefreshCw size={18} /> Requeue Task
                </button>
              )}
              {canRetry && (
                <button className="action-btn retry-btn" onClick={handleRetry}>
                  <RefreshCw size={18} /> Retry Task
                </button>
              )}
              {canCancel && (
                <button className="action-btn cancel-btn" onClick={handleCancel}>
                  <XCircle size={18} /> Cancel Task
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default TaskModal;
