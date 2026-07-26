import React from 'react';
import { CheckCircle2, XCircle, Loader2, PauseCircle, Clock, AlertCircle } from 'lucide-react';

const STATUS_CONFIG = {
  completed: {
    border: '#10b981',
    glow: 'rgba(16, 185, 129, 0.25)',
    bg: 'rgba(16, 185, 129, 0.06)',
    text: '#10b981',
    dot: '#10b981',
    label: 'Completed',
  },
  running: {
    border: '#3b82f6',
    glow: 'rgba(59, 130, 246, 0.35)',
    bg: 'rgba(59, 130, 246, 0.07)',
    text: '#3b82f6',
    dot: '#3b82f6',
    label: 'Running',
  },
  failed: {
    border: '#ef4444',
    glow: 'rgba(239, 68, 68, 0.25)',
    bg: 'rgba(239, 68, 68, 0.06)',
    text: '#ef4444',
    dot: '#ef4444',
    label: 'Failed',
  },
  paused: {
    border: '#f59e0b',
    glow: 'rgba(245, 158, 11, 0.2)',
    bg: 'rgba(245, 158, 11, 0.06)',
    text: '#f59e0b',
    dot: '#f59e0b',
    label: 'Paused',
  },
  cancelled: {
    border: 'rgba(255,255,255,0.1)',
    glow: 'none',
    bg: 'rgba(255,255,255,0.02)',
    text: 'rgba(255,255,255,0.3)',
    dot: 'rgba(255,255,255,0.2)',
    label: 'Cancelled',
  },
  waiting: {
    border: 'rgba(255,255,255,0.07)',
    glow: 'none',
    bg: 'rgba(255,255,255,0.01)',
    text: 'rgba(255,255,255,0.35)',
    dot: 'rgba(255,255,255,0.15)',
    label: 'Waiting',
  },
};

const StatusIcon = ({ status }) => {
  switch (status) {
    case 'completed': return <CheckCircle2 size={14} style={{ color: '#10b981' }} />;
    case 'running':   return <Loader2 size={14} className="animate-spin" style={{ color: '#3b82f6' }} />;
    case 'failed':    return <XCircle size={14} style={{ color: '#ef4444' }} />;
    case 'paused':    return <PauseCircle size={14} style={{ color: '#f59e0b' }} />;
    case 'cancelled': return <AlertCircle size={14} style={{ color: 'rgba(255,255,255,0.3)' }} />;
    default:          return <Clock size={14} style={{ color: 'rgba(255,255,255,0.2)' }} />;
  }
};

export const PipelineStage = ({ name, status, durationSeconds, retriesCount }) => {
  const key = status?.toLowerCase() || 'waiting';
  const cfg = STATUS_CONFIG[key] || STATUS_CONFIG.waiting;
  const isRunning = key === 'running';

  return (
    <>
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          padding: '14px 10px',
          borderRadius: '12px',
          border: `1.5px solid ${cfg.border}`,
          backgroundColor: cfg.bg,
          minWidth: '110px',
          maxWidth: '130px',
          textAlign: 'center',
          transition: 'all 0.3s ease',
          boxShadow: isRunning ? `0 0 16px ${cfg.glow}, 0 0 4px ${cfg.glow}` : 'none',
          position: 'relative',
          animation: isRunning ? 'stagePulse 2s ease-in-out infinite' : 'none',
        }}
      >
        {/* Icon */}
        <div style={{ marginBottom: '8px' }}>
          <StatusIcon status={key} />
        </div>

        {/* Stage name */}
        <span style={{
          fontSize: '11px',
          fontWeight: 600,
          color: cfg.text,
          lineHeight: 1.3,
          letterSpacing: '0.01em',
        }}>
          {name}
        </span>

        {/* Duration */}
        {durationSeconds !== undefined && durationSeconds > 0 && (
          <span style={{
            fontSize: '9px',
            color: 'rgba(255,255,255,0.35)',
            fontFamily: 'monospace',
            marginTop: '5px',
          }}>
            {durationSeconds}s
          </span>
        )}

        {/* Retry badge */}
        {retriesCount > 0 && (
          <span style={{
            fontSize: '8px',
            fontWeight: 700,
            color: '#ef4444',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            borderRadius: '3px',
            padding: '1px 5px',
            marginTop: '4px',
          }}>
            retry×{retriesCount}
          </span>
        )}

        {/* Running ring glow */}
        {isRunning && (
          <div style={{
            position: 'absolute',
            inset: -3,
            borderRadius: 14,
            border: `1px solid ${cfg.border}`,
            opacity: 0.4,
            animation: 'ringPulse 1.5s ease-in-out infinite',
            pointerEvents: 'none',
          }} />
        )}
      </div>

      <style>{`
        @keyframes stagePulse {
          0%, 100% { box-shadow: 0 0 16px ${cfg.glow}; }
          50%        { box-shadow: 0 0 28px ${cfg.glow}, 0 0 8px ${cfg.glow}; }
        }
        @keyframes ringPulse {
          0%, 100% { opacity: 0.3; transform: scale(1); }
          50%       { opacity: 0.7; transform: scale(1.04); }
        }
      `}</style>
    </>
  );
};

export default PipelineStage;
