import React from 'react';
import { FileText, RefreshCw, CheckCircle, AlertCircle, PauseCircle, Clock } from 'lucide-react';

const STATUS_META = {
  completed: { color: '#10b981', bg: 'rgba(16,185,129,0.08)', Icon: CheckCircle,  label: 'Completed'  },
  running:   { color: '#3b82f6', bg: 'rgba(59,130,246,0.08)',  Icon: RefreshCw,    label: 'Running'    },
  failed:    { color: '#ef4444', bg: 'rgba(239,68,68,0.08)',   Icon: AlertCircle,  label: 'Failed'     },
  paused:    { color: '#f59e0b', bg: 'rgba(245,158,11,0.08)',  Icon: PauseCircle,  label: 'Paused'     },
  idle:      { color: 'rgba(255,255,255,0.3)', bg: 'rgba(255,255,255,0.03)', Icon: Clock, label: 'Idle' },
};

const formatSize = (bytes) => {
  if (!bytes) return '0 B';
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
};

export const UploadCard = ({ filename, sizeBytes, pagesCount, uploadTime, status, activeWorker, activePriority, onReplace }) => {
  const key = status?.toLowerCase() || 'idle';
  const meta = STATUS_META[key] || STATUS_META.idle;
  const { color, bg, Icon, label } = meta;
  const isRunning = key === 'running';

  return (
    <div style={{
      background: 'rgba(15, 23, 42, 0.5)',
      border: `1px solid ${color}30`,
      borderRadius: '14px',
      padding: '24px',
      display: 'flex',
      flexDirection: 'column',
      gap: '20px',
      backdropFilter: 'blur(12px)',
      boxShadow: `0 4px 24px ${color}12`,
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Ambient glow strip */}
      <div style={{
        position: 'absolute',
        top: 0, left: 0, right: 0,
        height: 2,
        background: `linear-gradient(90deg, transparent, ${color}, transparent)`,
        opacity: 0.6,
      }} />

      {/* File info header */}
      <div style={{ display: 'flex', gap: '14px', alignItems: 'flex-start' }}>
        <div style={{
          width: 44, height: 44,
          borderRadius: '10px',
          background: 'rgba(59,130,246,0.1)',
          border: '1px solid rgba(59,130,246,0.2)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0,
        }}>
          <FileText size={20} style={{ color: '#3b82f6' }} />
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          <h4 style={{
            margin: '0 0 4px 0',
            fontSize: '0.9rem',
            fontWeight: 700,
            color: '#fff',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}>
            {filename}
          </h4>
          <div style={{ display: 'flex', gap: 10, fontSize: '12px', color: 'rgba(255,255,255,0.4)' }}>
            <span>{formatSize(sizeBytes)}</span>
            {pagesCount && <><span>·</span><span>{pagesCount} pages</span></>}
            {uploadTime && <><span>·</span><span>{uploadTime}</span></>}
          </div>
        </div>
      </div>

      {/* Status row */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: bg,
        border: `1px solid ${color}25`,
        borderRadius: '8px',
        padding: '10px 14px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Icon
            size={14}
            style={{ color, flexShrink: 0 }}
            className={isRunning ? 'animate-spin' : ''}
          />
          <span style={{ fontSize: '12px', fontWeight: 700, color }}>{label}</span>
        </div>
        {isRunning && (
          <div style={{ display: 'flex', gap: 3 }}>
            {[0, 1, 2].map(i => (
              <div key={i} style={{
                width: 3,
                height: 12,
                borderRadius: 2,
                background: '#3b82f6',
                animation: `barPulse 1s ease-in-out infinite`,
                animationDelay: `${i * 0.15}s`,
              }} />
            ))}
          </div>
        )}
      </div>

      {/* Worker tag */}
      <div style={{ display: 'flex', gap: 8 }}>
        {[activeWorker || 'Not Available', `priority: ${activePriority || 'Not Available'}`].map(tag => (
          <span key={tag} style={{
            fontSize: '10px',
            color: 'rgba(255,255,255,0.3)',
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.06)',
            borderRadius: 20,
            padding: '3px 10px',
          }}>
            {tag}
          </span>
        ))}
      </div>

      {/* Replace action */}
      <button
        onClick={onReplace}
        style={{
          background: 'rgba(255,255,255,0.03)',
          border: '1px solid rgba(255,255,255,0.08)',
          borderRadius: 8,
          color: 'rgba(255,255,255,0.5)',
          fontSize: '12px',
          padding: '8px 0',
          cursor: 'pointer',
          transition: 'all 0.2s',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 6,
          width: '100%',
        }}
        onMouseEnter={e => {
          e.currentTarget.style.borderColor = 'rgba(255,255,255,0.2)';
          e.currentTarget.style.color = '#fff';
        }}
        onMouseLeave={e => {
          e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)';
          e.currentTarget.style.color = 'rgba(255,255,255,0.5)';
        }}
      >
        Replace Document
      </button>

      <style>{`
        @keyframes barPulse {
          0%, 100% { opacity: 0.4; transform: scaleY(0.6); }
          50%       { opacity: 1;   transform: scaleY(1); }
        }
      `}</style>
    </div>
  );
};

export default UploadCard;
