import React, { useState } from 'react';
import { ChevronDown, ChevronRight, ShieldAlert, RefreshCw } from 'lucide-react';



export const ErrorPanel = ({ errors = [], onRetryTask }) => {
  const [expandedTaskId, setExpandedTaskId] = useState(null);
  const [loadingTaskId, setLoadingTaskId] = useState(null);
  const [retryErrors, setRetryErrors] = useState({}); // taskId -> error message string

  const handleTaskRetryClick = async (e, task, force = false) => {
    e.stopPropagation();
    if (loadingTaskId === task.id) return; // Reject duplicate clicks

    setLoadingTaskId(task.id);
    // Clear any previous retry error for this task
    setRetryErrors(prev => {
      const copy = { ...prev };
      delete copy[task.id];
      return copy;
    });

    try {
      await onRetryTask(task.id, force);
    } catch (err) {
      console.error(`Failed to retry task ${task.id}:`, err);
      // Retrieve the backend error message
      const errMsg = err.response?.data?.error || err.message || "Failed to trigger retry.";
      setRetryErrors(prev => ({
        ...prev,
        [task.id]: errMsg
      }));
    } finally {
      setLoadingTaskId(null);
    }
  };

  return (
    <div style={{
      background: 'rgba(15, 23, 42, 0.4)',
      border: errors.length > 0
        ? '1px solid rgba(239, 68, 68, 0.25)'
        : '1px solid rgba(255,255,255,0.05)',
      borderRadius: '14px',
      overflow: 'hidden',
      backdropFilter: 'blur(12px)',
    }}>
      {/* Panel header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '14px 18px',
        borderBottom: errors.length > 0
          ? '1px solid rgba(239,68,68,0.12)'
          : '1px solid rgba(255,255,255,0.04)',
        background: errors.length > 0 ? 'rgba(239,68,68,0.03)' : 'rgba(255,255,255,0.01)',
      }}>
        <ShieldAlert size={15} style={{ color: errors.length > 0 ? '#ef4444' : 'rgba(255,255,255,0.25)' }} />
        <span style={{
          fontSize: '11px',
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
          color: errors.length > 0 ? '#ef4444' : 'rgba(255,255,255,0.3)',
        }}>
          Airflow Fault Diagnostics
        </span>
        {errors.length > 0 && (
          <span style={{
            marginLeft: 'auto',
            fontSize: '10px',
            background: 'rgba(239,68,68,0.12)',
            border: '1px solid rgba(239,68,68,0.25)',
            color: '#ef4444',
            borderRadius: 20,
            padding: '1px 8px',
            fontWeight: 700,
          }}>
            {errors.length} fault{errors.length > 1 ? 's' : ''}
          </span>
        )}
      </div>

      {/* Body */}
      {errors.length === 0 ? (
        <div style={{
          padding: '30px 24px',
          textAlign: 'center',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 8,
        }}>
          <div style={{
            width: 36, height: 36,
            borderRadius: '50%',
            background: 'rgba(16,185,129,0.07)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          </div>
          <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.35)' }}>No pipeline faults detected</span>
          <span style={{ fontSize: '10.5px', color: 'rgba(255,255,255,0.2)' }}>All execution tasks operating normally</span>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
          {errors.map((err) => {
            const expanded = expandedTaskId === err.id;
            const accent = '#ef4444'; // Capitalized statuses FAILED and CANCELLED are error level accent
            
            const retriesText = `${err.retries} / ${err.maxRetries}`;
            const queueWaitText = typeof err.queueWait === 'number' ? `${err.queueWait.toFixed(2)} s` : 'Not Available';
            const executionDurationText = typeof err.executionDuration === 'number' ? `${err.executionDuration.toFixed(2)} s` : 'Not Available';
            
            // Format state status verbatim (e.g. FAILED, CANCELLED)
            const statusDisplay = String(err.status || 'failed').toUpperCase();
            
            const isTaskLoading = loadingTaskId === err.id;
            const retryErrorMsg = retryErrors[err.id];
            
            // Force Retry action is disabled because the backend does not expose a machine-readable force indicator.
            const showForceRetry = false;

            return (
              <div key={err.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                {/* Accordion header */}
                <div
                  onClick={() => setExpandedTaskId(expanded ? null : err.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 12,
                    padding: '14px 18px',
                    cursor: 'pointer',
                    userSelect: 'none',
                    transition: 'background 0.15s',
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.02)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                >
                  <span style={{
                    fontSize: '9px',
                    fontWeight: 700,
                    letterSpacing: '0.05em',
                    padding: '2px 7px',
                    borderRadius: 4,
                    background: `${accent}14`,
                    color: accent,
                    border: `1px solid ${accent}30`,
                    flexShrink: 0,
                  }}>
                    {err.stage?.toUpperCase() || 'FAULT'}
                  </span>

                  <span style={{
                    fontSize: '9px',
                    fontWeight: 700,
                    letterSpacing: '0.05em',
                    padding: '2px 7px',
                    borderRadius: 4,
                    background: 'rgba(255, 255, 255, 0.05)',
                    color: '#94a3b8',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    flexShrink: 0,
                  }}>
                    {statusDisplay}
                  </span>

                  <span style={{ fontSize: '12px', fontWeight: 600, color: '#fff', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {err.message}
                  </span>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'rgba(255,255,255,0.3)', fontSize: '10px', fontFamily: 'monospace', flexShrink: 0 }}>
                    <span>{err.timestamp}</span>
                    {expanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
                  </div>
                </div>

                {/* Expanded Airflow-style fault details (strictly read-only) */}
                {expanded && (
                  <div style={{
                    padding: '16px 18px 20px',
                    borderTop: '1px solid rgba(255,255,255,0.04)',
                    background: 'rgba(0,0,0,0.25)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 14,
                    fontSize: '11px',
                    fontFamily: "'JetBrains Mono', monospace",
                  }}>
                    {/* Airflow Properties grid */}
                    <div style={{
                      display: 'grid',
                      gridTemplateColumns: '150px 1fr',
                      gap: '6px 12px',
                      color: 'rgba(255,255,255,0.6)',
                    }}>
                      {[
                        ['Stage Name', err.stage || 'Not Available'],
                        ['Worker ID', err.worker || 'Not Available'],
                        ['Retry Progress', retriesText],
                        ['Queue Wait Time', queueWaitText],
                        ['Execution Duration', executionDurationText],
                      ].map(([k, v]) => (
                        <React.Fragment key={k}>
                          <span style={{ color: 'rgba(255,255,255,0.35)' }}>{k}:</span>
                          <span style={{ color: '#fff', fontWeight: 500 }}>{v}</span>
                        </React.Fragment>
                      ))}
                    </div>

                    {/* Backend Diagnostic Message */}
                    {err.message && (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                        <span style={{ color: 'rgba(255,255,255,0.35)' }}>Backend Diagnostic Message:</span>
                        <pre style={{
                          margin: 0,
                          padding: '12px 14px',
                          background: 'rgba(0,0,0,0.5)',
                          border: '1px solid rgba(255,255,255,0.06)',
                          borderRadius: 8,
                          overflowX: 'auto',
                          color: '#ef4444',
                          fontSize: '10.5px',
                          lineHeight: 1.6,
                        }}>
                          {err.message}
                        </pre>
                      </div>
                    )}

                    {/* Error display from failed retry trigger */}
                    {retryErrorMsg && (
                      <div style={{
                        padding: '10px 14px',
                        background: 'rgba(239,68,68,0.05)',
                        border: '1px solid rgba(239,68,68,0.25)',
                        borderRadius: 8,
                        color: '#ef4444',
                        fontSize: '11px',
                      }}>
                        <strong>Retry Failed:</strong> {retryErrorMsg}
                      </div>
                    )}

                    {/* Interactive Retry Trigger */}
                    {onRetryTask && (
                      <div style={{ display: 'flex', gap: 10 }}>
                        <button
                          onClick={(e) => handleTaskRetryClick(e, err, false)}
                          disabled={loadingTaskId !== null}
                          aria-label={`Retry task ${err.stage}`}
                          style={{
                            alignSelf: 'flex-start',
                            display: 'flex',
                            alignItems: 'center',
                            gap: 6,
                            background: isTaskLoading ? 'rgba(59,130,246,0.2)' : 'rgba(59,130,246,0.1)',
                            border: '1px solid rgba(59,130,246,0.3)',
                            color: '#3b82f6',
                            borderRadius: 6,
                            padding: '6px 14px',
                            fontSize: '11px',
                            cursor: loadingTaskId !== null ? 'not-allowed' : 'pointer',
                            opacity: loadingTaskId !== null && !isTaskLoading ? 0.5 : 1,
                            fontWeight: 600,
                            transition: 'all 0.2s',
                          }}
                          onMouseEnter={e => { if (loadingTaskId === null) e.currentTarget.style.background = 'rgba(59,130,246,0.18)'; }}
                          onMouseLeave={e => { if (loadingTaskId === null) e.currentTarget.style.background = 'rgba(59,130,246,0.1)'; }}
                        >
                          <RefreshCw size={12} className={isTaskLoading ? "spin" : ""} style={{ animation: isTaskLoading ? "spin 1s linear infinite" : "none" }} />
                          {isTaskLoading ? 'Retrying Task...' : 'Retry Task Stage'}
                        </button>

                        {showForceRetry && (
                          <button
                            onClick={(e) => handleTaskRetryClick(e, err, true)}
                            disabled={loadingTaskId !== null}
                            aria-label={`Force retry task ${err.stage}`}
                            style={{
                              alignSelf: 'flex-start',
                              display: 'flex',
                              alignItems: 'center',
                              gap: 6,
                              background: 'rgba(239, 68, 68, 0.1)',
                              border: '1px solid rgba(239, 68, 68, 0.3)',
                              color: '#ef4444',
                              borderRadius: 6,
                              padding: '6px 14px',
                              fontSize: '11px',
                              cursor: loadingTaskId !== null ? 'not-allowed' : 'pointer',
                              fontWeight: 600,
                              transition: 'all 0.2s',
                            }}
                            onMouseEnter={e => { if (loadingTaskId === null) e.currentTarget.style.background = 'rgba(239, 68, 68, 0.18)'; }}
                            onMouseLeave={e => { if (loadingTaskId === null) e.currentTarget.style.background = 'rgba(239, 68, 68, 0.1)'; }}
                          >
                            <RefreshCw size={12} />
                            Force Retry Stage
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .spin {
          animation: spin 1s linear infinite;
        }
      `}</style>
    </div>
  );
};

export default ErrorPanel;
