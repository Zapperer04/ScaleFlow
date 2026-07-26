import React from 'react';
import { Lock, RefreshCw, AlertCircle, PauseCircle } from 'lucide-react';

/**
 * ChatLockScreen — shown in the right chat panel when the pipeline has not
 * yet completed.
 *
 * Props:
 *   currentStage  — task_type of the currently-running backend task, or null
 *   status        — pipeline status string from backend (running/paused/failed/idle)
 *
 * NOTE: etaSeconds was removed. The backend does not expose an ETA value.
 * Displaying a fabricated countdown is worse than showing nothing.
 */
export const ChatLockScreen = ({ currentStage, status }) => {
  const isFailed  = status?.toLowerCase() === 'failed';
  const isPaused  = status?.toLowerCase() === 'paused';
  const isIdle    = !status || status.toLowerCase() === 'idle';
  const isRunning = status?.toLowerCase() === 'running';

  const accentColor = isFailed ? '#ef4444' : isPaused ? '#f59e0b' : '#3b82f6';
  const bgGlow      = isFailed ? 'rgba(239,68,68,0.06)' : isPaused ? 'rgba(245,158,11,0.06)' : 'rgba(59,130,246,0.06)';

  const getMessage = () => {
    if (isFailed) return 'Ingestion pipeline encountered a fatal error. Review the Error Inspector above and retry.';
    if (isPaused) return 'Pipeline is paused. Resume execution to continue document processing.';
    if (isIdle)   return 'Upload a document to begin the AI ingestion pipeline.';
    return 'Chat unlocks automatically once all pipeline stages complete successfully.';
  };

  const getTitle = () => {
    if (isFailed) return 'Pipeline Failed';
    if (isPaused) return 'Pipeline Paused';
    if (isIdle)   return 'No Active Document';
    return 'Chat Locked';
  };

  const LockIcon = isFailed ? AlertCircle : isPaused ? PauseCircle : Lock;

  return (
    <div style={{
      background: `linear-gradient(135deg, rgba(15,23,42,0.6) 0%, ${bgGlow} 100%)`,
      border: `1px solid ${accentColor}25`,
      borderRadius: '16px',
      padding: '60px 40px',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      textAlign: 'center',
      gap: '28px',
      minHeight: '340px',
      backdropFilter: 'blur(16px)',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Background radial glow */}
      <div style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        width: 280,
        height: 280,
        borderRadius: '50%',
        background: `radial-gradient(circle, ${accentColor}08, transparent 70%)`,
        pointerEvents: 'none',
        animation: isRunning ? 'lockGlow 3s ease-in-out infinite' : 'none',
      }} />

      {/* Lock icon */}
      <div style={{
        position: 'relative',
        width: 72,
        height: 72,
        borderRadius: '50%',
        background: `${accentColor}12`,
        border: `1px solid ${accentColor}30`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        animation: isRunning ? 'lockFloat 3s ease-in-out infinite' : 'none',
      }}>
        <LockIcon size={28} style={{ color: accentColor }} />

        {/* Pulsing ring for running state */}
        {isRunning && (
          <>
            <div style={{
              position: 'absolute', inset: -8,
              borderRadius: '50%',
              border: `1px solid ${accentColor}40`,
              animation: 'ringExpand 2s ease-out infinite',
            }} />
            <div style={{
              position: 'absolute', inset: -16,
              borderRadius: '50%',
              border: `1px solid ${accentColor}20`,
              animation: 'ringExpand 2s ease-out 0.6s infinite',
            }} />
          </>
        )}
      </div>

      {/* Text */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxWidth: 380 }}>
        <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 700, color: '#fff' }}>
          {getTitle()}
        </h3>
        <p style={{ margin: 0, fontSize: '0.85rem', color: 'rgba(255,255,255,0.45)', lineHeight: 1.6 }}>
          {getMessage()}
        </p>
      </div>

      {/* Current stage indicator — only shown when running and backend provides a stage */}
      {isRunning && currentStage && (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 0,
          background: 'rgba(0,0,0,0.25)',
          border: '1px solid rgba(255,255,255,0.07)',
          borderRadius: 10,
          overflow: 'hidden',
          width: '100%',
          maxWidth: 340,
          fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
          fontSize: '11px',
        }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '11px 16px',
          }}>
            <span style={{ color: 'rgba(255,255,255,0.3)' }}>Current Stage</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6, color: accentColor }}>
              <RefreshCw size={10} className="animate-spin" />
              {currentStage}
            </span>
          </div>
        </div>
      )}

      <style>{`
        @keyframes lockFloat {
          0%, 100% { transform: translateY(0); }
          50%       { transform: translateY(-6px); }
        }
        @keyframes lockGlow {
          0%, 100% { opacity: 0.5; }
          50%       { opacity: 1; }
        }
        @keyframes ringExpand {
          0%   { transform: scale(1); opacity: 0.7; }
          100% { transform: scale(1.6); opacity: 0; }
        }
      `}</style>
    </div>
  );
};

export default ChatLockScreen;
