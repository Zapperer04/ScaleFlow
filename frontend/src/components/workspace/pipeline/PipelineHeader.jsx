import React, { useEffect, useState } from 'react';
import { Activity, Clock } from 'lucide-react';

export const PipelineHeader = ({ pipelineId, documentName, workerId, status, elapsedSeconds, etaSeconds, queuePosition, startTime }) => {
  const [liveElapsed, setLiveElapsed] = useState(elapsedSeconds || 0);

  useEffect(() => {
    setLiveElapsed(elapsedSeconds || 0);
  }, [elapsedSeconds]);

  // Elapsed timer increment every second when running
  useEffect(() => {
    if (status?.toLowerCase() !== 'running') return;
    
    const interval = setInterval(() => {
      setLiveElapsed((prev) => prev + 1);
    }, 1000);
    
    return () => clearInterval(interval);
  }, [status]);

  const formatDuration = (sec) => {
    if (sec === undefined || sec === null || isNaN(sec)) return '00:00';
    const m = Math.floor(sec / 60).toString().padStart(2, '0');
    const s = (sec % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  const getStatusBg = (s) => {
    switch (s?.toLowerCase()) {
      case 'completed': return 'rgba(16, 185, 129, 0.08)';
      case 'running': return 'rgba(79, 70, 229, 0.08)';
      case 'failed': return 'rgba(244, 63, 94, 0.08)';
      case 'paused': return 'rgba(245, 158, 11, 0.08)';
      default: return 'rgba(255, 255, 255, 0.02)';
    }
  };

  const getStatusColor = (s) => {
    switch (s?.toLowerCase()) {
      case 'completed': return 'var(--color-success)';
      case 'running': return 'var(--color-accent)';
      case 'failed': return 'var(--color-failure)';
      case 'paused': return 'var(--color-warning)';
      default: return 'var(--text-muted)';
    }
  };

  return (
    <div
      style={{
        backgroundColor: 'var(--bg-panel)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-14)',
        padding: 'var(--spacing-20)',
        display: 'flex',
        flexWrap: 'wrap',
        gap: 'var(--spacing-24)',
        alignItems: 'center',
        justifyContent: 'space-between',
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      {/* Brand Identity / Title info */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-16)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '40px', height: '40px', borderRadius: '50%', backgroundColor: getStatusBg(status), color: getStatusColor(status) }}>
          <Activity size={18} className={status?.toLowerCase() === 'running' ? 'animate-pulse' : ''} />
        </div>
        <div>
          <span style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
            PIPELINE {pipelineId ? `#${pipelineId}` : 'NONE'}
          </span>
          <h2 style={{ fontSize: 'var(--font-size-base)', fontWeight: 600, margin: '2px 0 0 0', color: 'var(--text-primary)', maxWidth: '280px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {documentName || 'No Active Document'}
          </h2>
        </div>
      </div>

      {/* Metric blocks */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--spacing-32)', flex: 1, justifyContent: 'flex-end', minWidth: '280px' }}>
        
        {/* Worker ID */}
        <div>
          <span style={{ display: 'block', fontSize: '9px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Worker</span>
          <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 600, color: 'var(--text-secondary)' }}>{workerId || 'Unassigned'}</span>
        </div>

        {/* Status */}
        <div>
          <span style={{ display: 'block', fontSize: '9px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Status</span>
          <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, color: getStatusColor(status) }}>{status || 'Idle'}</span>
        </div>

        {/* Elapsed duration */}
        <div>
          <span style={{ fontSize: '9px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '2px' }}>
            <Clock size={9} /> Elapsed
          </span>
          <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 600, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
            {formatDuration(liveElapsed)}
          </span>
        </div>

        {/* ETA removed — backend does not expose an estimated time to completion.
            Displaying formatDuration(undefined) = "00:00" would be a fabricated value. */}

        {/* Queue Position */}
        {queuePosition !== undefined && queuePosition > 0 && (
          <div>
            <span style={{ display: 'block', fontSize: '9px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Queue Position</span>
            <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 600, color: 'var(--color-warning)' }}>#{queuePosition}</span>
          </div>
        )}

        {/* Started Time */}
        {startTime && (
          <div>
            <span style={{ display: 'block', fontSize: '9px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Started</span>
            <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 500, color: 'var(--text-secondary)' }}>{startTime}</span>
          </div>
        )}
      </div>
    </div>
  );
};
export default PipelineHeader;
