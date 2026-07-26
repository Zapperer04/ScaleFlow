import React, { useState } from 'react';
import { ChevronDown, ChevronRight, ShieldAlert, RefreshCw } from 'lucide-react';

const ToolIcon = ({ size }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
  </svg>
);

export const ErrorPanel = ({ errors = [], onRetry }) => {
  const [expandedIndex, setExpandedIndex] = useState(null);

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
          {errors.map((err, idx) => {
            const expanded = expandedIndex === idx;
            const isErr    = err.level?.toLowerCase() === 'error';
            const accent   = isErr ? '#ef4444' : '#f59e0b';
            const isRecoverable = err.recoverable !== false;
            const retriesText = `${err.retries || 0} / ${err.maxRetries || 3}`;

            return (
              <div key={idx} style={{ borderBottom: idx < errors.length - 1 ? '1px solid rgba(255,255,255,0.04)' : 'none' }}>
                {/* Accordion header */}
                <div
                  onClick={() => setExpandedIndex(expanded ? null : idx)}
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

                  <span style={{ fontSize: '12px', fontWeight: 600, color: '#fff', flex: 1 }}>
                    {err.message}
                  </span>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'rgba(255,255,255,0.3)', fontSize: '10px', fontFamily: 'monospace', flexShrink: 0 }}>
                    <span>{err.timestamp}</span>
                    {expanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
                  </div>
                </div>

                {/* Expanded Airflow-style fault details */}
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
                      gridTemplateColumns: '120px 1fr',
                      gap: '6px 12px',
                      color: 'rgba(255,255,255,0.6)',
                    }}>
                      {[
                        ['Stage', err.stage || 'Unknown'],
                        ['Worker ID', err.worker || 'Unassigned'],
                        ['Recoverable', isRecoverable ? 'YES (Auto-recovery supported)' : 'NO (Fatal stage failure)'],
                        ['Retry Progress', retriesText],
                        ['Queue Wait Time', err.queueWait ? `${err.queueWait}s` : 'Not Available'],
                        ['Execution Duration', err.executionDuration ? `${err.executionDuration}s` : 'Not Available'],
                      ].map(([k, v]) => (
                        <React.Fragment key={k}>
                          <span style={{ color: 'rgba(255,255,255,0.35)' }}>{k}:</span>
                          <span style={{ color: '#fff', fontWeight: 500 }}>{v}</span>
                        </React.Fragment>
                      ))}
                    </div>

                    {/* Suggested fix */}
                    {err.suggestedFix && (
                      <div style={{
                        display: 'flex',
                        gap: 10,
                        alignItems: 'flex-start',
                        padding: '10px 14px',
                        background: 'rgba(16,185,129,0.05)',
                        border: '1px solid rgba(16,185,129,0.2)',
                        borderRadius: 8,
                        color: '#10b981',
                        fontSize: '11px',
                      }}>
                        <ToolIcon size={13} style={{ flexShrink: 0, marginTop: 1 }} />
                        <div>
                          <strong>Suggested Action:</strong><br />
                          {err.suggestedFix}
                        </div>
                      </div>
                    )}

                    {/* Stack trace */}
                    {err.stackTrace && (
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
                        {err.stackTrace}
                      </pre>
                    )}

                    {/* Interactive Retry Trigger */}
                    {onRetry && (
                      <button
                        onClick={() => onRetry(err)}
                        style={{
                          alignSelf: 'flex-start',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 6,
                          background: 'rgba(59,130,246,0.1)',
                          border: '1px solid rgba(59,130,246,0.3)',
                          color: '#3b82f6',
                          borderRadius: 6,
                          padding: '6px 14px',
                          fontSize: '11px',
                          cursor: 'pointer',
                          fontWeight: 600,
                          transition: 'all 0.2s',
                        }}
                        onMouseEnter={e => e.currentTarget.style.background = 'rgba(59,130,246,0.18)'}
                        onMouseLeave={e => e.currentTarget.style.background = 'rgba(59,130,246,0.1)'}
                      >
                        <RefreshCw size={12} />
                        Retry Task Stage
                      </button>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default ErrorPanel;
