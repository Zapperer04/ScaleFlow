import React, { useState, useEffect } from 'react';
import { X, RefreshCw, XCircle, AlertCircle } from 'lucide-react';
import { getTaskDetails, retryTask, cancelTask } from '../services/api';
import { formatTimeIST } from '../utils/timeUtils';

const TaskModal = ({ taskId, onClose, onActionComplete }) => {
  const [details, setDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [countdown, setCountdown] = useState(null);

  useEffect(() => {
    let timer = null;
    if (details && details.status === 'paused_rate_limit') {
      const progress = details.progress_json || {};
      const retryAfter = progress.retry_after_seconds || 0;
      setCountdown(retryAfter);
      timer = setInterval(() => {
        setCountdown(prev => {
          if (prev === null) return 0;
          if (prev <= 1) {
            clearInterval(timer);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } else {
      setCountdown(null);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [details]);

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

            {details.type === 'parse_document' && details.progress_json && (() => {
              const progress = details.progress_json;
              const total = progress.total_pages || 1;
              const completed = progress.completed_pages_count || progress.completed_pages?.length || 0;
              const pct = Math.min(100, Math.round((completed / total) * 100));
              const isPaused = details.status === 'paused_rate_limit';
              const parserName = progress.parser || 'Gemini';
              
              return (
                <div className="detail-section progress-section" style={{
                  background: 'rgba(30, 41, 59, 0.5)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '12px',
                  padding: '16px',
                  marginTop: '16px',
                  marginBottom: '16px'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#f8fafc' }}>
                      Parsing Progress ({parserName === 'gemini' ? 'Gemini VLM' : parserName.toUpperCase()})
                    </h3>
                    <span style={{ fontSize: '0.9rem', fontWeight: '600', color: '#3b82f6' }}>
                      {pct}% ({completed} / {total} pages)
                    </span>
                  </div>

                  <div className="progress-bar-container" style={{
                    width: '100%',
                    height: '10px',
                    background: '#1e293b',
                    borderRadius: '5px',
                    overflow: 'hidden',
                    marginBottom: '15px',
                    border: '1px solid rgba(255,255,255,0.05)'
                  }}>
                    <div className="progress-bar-fill" style={{
                      width: `${pct}%`,
                      height: '100%',
                      background: isPaused 
                        ? 'linear-gradient(90deg, #f59e0b, #ef4444)' 
                        : 'linear-gradient(90deg, #3b82f6, #10b981)',
                      borderRadius: '5px',
                      transition: 'width 0.4s ease-in-out',
                      boxShadow: isPaused 
                        ? '0 0 8px rgba(245, 158, 11, 0.5)' 
                        : '0 0 8px rgba(59, 130, 246, 0.5)'
                    }}></div>
                  </div>

                  {isPaused && (
                    <div style={{
                      background: 'rgba(239, 68, 68, 0.1)',
                      border: '1px solid rgba(239, 68, 68, 0.2)',
                      borderRadius: '8px',
                      padding: '12px',
                      marginBottom: '15px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px',
                      color: '#fca5a5'
                    }}>
                      <AlertCircle size={20} style={{ color: '#ef4444' }} />
                      <div>
                        <strong style={{ display: 'block', color: '#f87171' }}>Gemini Rate Limit Reached</strong>
                        <span style={{ fontSize: '0.9rem' }}>
                          Parsing paused. Waiting {countdown !== null ? countdown : (progress.retry_after_seconds || 0)} seconds before continuing...
                        </span>
                      </div>
                    </div>
                  )}

                  {!isPaused && details.status === 'running' && (
                    <div style={{
                      background: 'rgba(16, 185, 129, 0.1)',
                      border: '1px solid rgba(16, 185, 129, 0.2)',
                      borderRadius: '8px',
                      padding: '10px 12px',
                      marginBottom: '15px',
                      fontSize: '0.9rem',
                      color: '#a7f3d0'
                    }}>
                      <span>Parsing active. Resuming/processing from page {completed + 1}...</span>
                    </div>
                  )}

                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
                    gap: '12px',
                    fontSize: '0.85rem'
                  }}>
                    <div style={{ background: 'rgba(255,255,255,0.02)', padding: '8px', borderRadius: '6px' }}>
                      <span style={{ color: '#94a3b8', display: 'block' }}>Remaining Pages</span>
                      <span style={{ fontWeight: '600', color: '#e2e8f0' }}>{progress.remaining_pages ?? (total - completed)}</span>
                    </div>
                    <div style={{ background: 'rgba(255,255,255,0.02)', padding: '8px', borderRadius: '6px' }}>
                      <span style={{ color: '#94a3b8', display: 'block' }}>Estimated ETA</span>
                      <span style={{ fontWeight: '600', color: '#e2e8f0' }}>{progress.estimated_completion_time || 'Calculating...'}</span>
                    </div>
                    <div style={{ background: 'rgba(255,255,255,0.02)', padding: '8px', borderRadius: '6px' }}>
                      <span style={{ color: '#94a3b8', display: 'block' }}>Processing Speed</span>
                      <span style={{ fontWeight: '600', color: '#e2e8f0' }}>{progress.pages_per_minute || 0} pages/min</span>
                    </div>
                    <div style={{ background: 'rgba(255,255,255,0.02)', padding: '8px', borderRadius: '6px' }}>
                      <span style={{ color: '#94a3b8', display: 'block' }}>Gemini Requests</span>
                      <span style={{ fontWeight: '600', color: '#e2e8f0' }}>{progress.gemini_requests_sent || 0}</span>
                    </div>
                    <div style={{ background: 'rgba(255,255,255,0.02)', padding: '8px', borderRadius: '6px' }}>
                      <span style={{ color: '#94a3b8', display: 'block' }}>429 Count</span>
                      <span style={{ fontWeight: '600', color: '#ef4444' }}>{progress["429_count"] || 0}</span>
                    </div>
                    <div style={{ background: 'rgba(255,255,255,0.02)', padding: '8px', borderRadius: '6px' }}>
                      <span style={{ color: '#94a3b8', display: 'block' }}>Checkpoint Count</span>
                      <span style={{ fontWeight: '600', color: '#10b981' }}>{progress.checkpoint_count || 0}</span>
                    </div>
                  </div>
                </div>
              );
            })()}

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
