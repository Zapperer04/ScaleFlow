import React, { useState } from 'react';
import { Play, Pause, XCircle, RefreshCw, UploadCloud, Trash2, AlertTriangle } from 'lucide-react';

const CtrlBtn = ({ Icon, label, color = 'rgba(255,255,255,0.6)', bg = 'rgba(255,255,255,0.04)', borderColor = 'rgba(255,255,255,0.08)', onClick, disabled }) => (
  <button
    onClick={onClick}
    disabled={disabled}
    title={label}
    style={{
      display: 'flex',
      alignItems: 'center',
      gap: 7,
      background: bg,
      border: `1px solid ${borderColor}`,
      borderRadius: 8,
      color,
      fontSize: '12px',
      fontWeight: 600,
      padding: '8px 14px',
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.4 : 1,
      transition: 'all 0.18s ease',
      whiteSpace: 'nowrap',
    }}
    onMouseEnter={e => !disabled && (e.currentTarget.style.opacity = '0.85')}
    onMouseLeave={e => !disabled && (e.currentTarget.style.opacity = '1')}
  >
    <Icon size={14} />
    {label}
  </button>
);

const ConfirmModal = ({ title, body, confirmLabel, confirmDanger, onConfirm, onCancel }) => (
  <div style={{
    position: 'fixed', inset: 0,
    background: 'rgba(0,0,0,0.7)',
    backdropFilter: 'blur(6px)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    zIndex: 2000,
    animation: 'fadeIn 0.15s ease',
  }}>
    <div style={{
      background: 'rgba(15, 23, 42, 0.95)',
      border: '1px solid rgba(255,255,255,0.08)',
      borderRadius: 14,
      padding: '32px',
      maxWidth: 400,
      width: '100%',
      display: 'flex',
      flexDirection: 'column',
      gap: 20,
      boxShadow: '0 16px 64px rgba(0,0,0,0.6)',
      animation: 'slideUp 0.2s ease',
    }}>
      <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
        <div style={{
          width: 40, height: 40, borderRadius: '50%',
          background: 'rgba(239,68,68,0.1)',
          border: '1px solid rgba(239,68,68,0.2)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0,
        }}>
          <AlertTriangle size={18} style={{ color: '#ef4444' }} />
        </div>
        <div>
          <h4 style={{ margin: '0 0 6px', fontSize: '1rem', fontWeight: 700, color: '#fff' }}>{title}</h4>
          <p style={{ margin: 0, fontSize: '0.83rem', color: 'rgba(255,255,255,0.5)', lineHeight: 1.5 }}>{body}</p>
        </div>
      </div>
      <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
        <button
          onClick={onCancel}
          style={{
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 7,
            color: 'rgba(255,255,255,0.6)',
            fontSize: '12px',
            fontWeight: 600,
            padding: '8px 18px',
            cursor: 'pointer',
          }}
        >
          Cancel
        </button>
        <button
          onClick={onConfirm}
          style={{
            background: confirmDanger ? 'rgba(239,68,68,0.15)' : 'rgba(59,130,246,0.15)',
            border: `1px solid ${confirmDanger ? 'rgba(239,68,68,0.4)' : 'rgba(59,130,246,0.4)'}`,
            borderRadius: 7,
            color: confirmDanger ? '#ef4444' : '#3b82f6',
            fontSize: '12px',
            fontWeight: 700,
            padding: '8px 18px',
            cursor: 'pointer',
          }}
        >
          {confirmLabel}
        </button>
      </div>
    </div>
    <style>{`
      @keyframes fadeIn  { from { opacity: 0; } to { opacity: 1; } }
      @keyframes slideUp { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
    `}</style>
  </div>
);

export const PipelineControls = ({ status, onPause, onResume, onCancel, onRetry, onReupload, onDelete }) => {
  const [modal, setModal] = useState(null);   // 'cancel' | 'delete'

  const s = status?.toLowerCase() || '';
  const isRunning   = s === 'running';
  const isPaused    = s === 'paused';
  const isFailed    = s === 'failed';
  const isCompleted = s === 'completed';
  const isCancelled = s === 'cancelled';
  const canReplace  = isCompleted || isFailed || isCancelled;

  const confirmModal = (type) => setModal(type);
  const closeModal   = ()     => setModal(null);

  const handleConfirm = () => {
    if (modal === 'cancel') { onCancel?.(); }
    if (modal === 'delete') { onDelete?.(); }
    closeModal();
  };

  return (
    <>
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: 8,
        alignItems: 'center',
      }}>
        {/* Pause */}
        {isRunning && (
          <CtrlBtn
            Icon={Pause}
            label="Pause"
            onClick={onPause}
            bg="rgba(245,158,11,0.08)"
            borderColor="rgba(245,158,11,0.2)"
            color="#f59e0b"
          />
        )}

        {/* Resume */}
        {isPaused && (
          <CtrlBtn
            Icon={Play}
            label="Resume"
            onClick={onResume}
            bg="rgba(59,130,246,0.1)"
            borderColor="rgba(59,130,246,0.3)"
            color="#3b82f6"
          />
        )}

        {/* Cancel (requires confirmation) */}
        {(isRunning || isPaused) && (
          <CtrlBtn
            Icon={XCircle}
            label="Cancel"
            onClick={() => confirmModal('cancel')}
            bg="rgba(239,68,68,0.06)"
            borderColor="rgba(239,68,68,0.2)"
            color="#ef4444"
          />
        )}

        {/* Retry */}
        {isFailed && (
          <CtrlBtn
            Icon={RefreshCw}
            label="Retry"
            onClick={onRetry}
            bg="rgba(59,130,246,0.1)"
            borderColor="rgba(59,130,246,0.3)"
            color="#3b82f6"
          />
        )}

        {/* Re-upload */}
        {canReplace && (
          <CtrlBtn
            Icon={UploadCloud}
            label="Re-upload"
            onClick={onReupload}
          />
        )}

        {/* Delete (requires confirmation) */}
        <CtrlBtn
          Icon={Trash2}
          label="Delete"
          onClick={() => confirmModal('delete')}
          bg="rgba(239,68,68,0.05)"
          borderColor="rgba(239,68,68,0.15)"
          color="#ef4444"
        />
      </div>

      {/* Modals */}
      {modal === 'cancel' && (
        <ConfirmModal
          title="Cancel Pipeline?"
          body="This will stop the ingestion job mid-flight. Partial results may be discarded. You can retry later."
          confirmLabel="Yes, Cancel"
          confirmDanger
          onConfirm={handleConfirm}
          onCancel={closeModal}
        />
      )}
      {modal === 'delete' && (
        <ConfirmModal
          title="Delete Pipeline?"
          body="All ingested vectors, graph nodes, and document caches will be permanently removed. This action cannot be undone."
          confirmLabel="Delete Permanently"
          confirmDanger
          onConfirm={handleConfirm}
          onCancel={closeModal}
        />
      )}
    </>
  );
};

export default PipelineControls;
