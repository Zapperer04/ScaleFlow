import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import ConsoleToolbar from './ConsoleToolbar';
import { usePipeline } from '../../../contexts/PipelineContext';

const LEVEL_STYLE = {
  ERROR:   { color: '#ef4444', label: 'ERR ' },
  WARNING: { color: '#f59e0b', label: 'WARN' },
  INFO:    { color: '#3b82f6', label: 'INFO' },
};

const LogRow = React.memo(({ log, isSelected, isReplayActiveEvent, onClick }) => {
  const ls = LEVEL_STYLE[log.level] || LEVEL_STYLE.INFO;
  return (
    <div
      onClick={onClick}
      style={{
        display: 'flex',
        gap: 10,
        alignItems: 'baseline',
        animation: 'fadeInLog 0.12s ease-out',
        padding: '3px 8px',
        borderRadius: 4,
        cursor: 'pointer',
        background: isReplayActiveEvent 
          ? 'rgba(167, 139, 250, 0.15)' 
          : isSelected 
            ? 'rgba(59, 130, 246, 0.12)' 
            : 'transparent',
        borderLeft: isReplayActiveEvent
          ? '3px solid #a78bfa'
          : isSelected 
            ? '3px solid #3b82f6' 
            : '3px solid transparent',
        transition: 'background 0.15s, border-left 0.15s',
      }}
      className="log-row-hover"
    >
      {/* Timestamp */}
      <span style={{ color: 'rgba(255,255,255,0.2)', fontSize: '10.5px', flexShrink: 0, userSelect: 'none' }}>
        {log.displayTime}
      </span>

      {/* Level badge */}
      <span style={{
        color: ls.color,
        fontWeight: 700,
        fontSize: '10px',
        flexShrink: 0,
        letterSpacing: '0.05em',
      }}>
        {ls.label}
      </span>

      {/* Worker */}
      <span style={{ color: 'rgba(255,255,255,0.4)', flexShrink: 0, fontSize: '10.5px' }}>
        {log.worker_id || 'system'}
      </span>

      {/* Task Type */}
      {log.task_type && log.task_type !== 'unknown' && (
        <span style={{ color: 'rgba(255,255,255,0.35)', flexShrink: 0, fontSize: '10.5px' }}>
          {log.task_type}:
        </span>
      )}

      {/* Message */}
      <span style={{ color: 'rgba(255,255,255,0.75)', flex: 1, wordBreak: 'break-all' }}>
        {log.message}
      </span>
    </div>
  );
});

export const ExecutionConsole = ({ events = [], loading = false, error = null }) => {
  const {
    selectedTaskId, setSelectedTaskId,
    selectedTraceId, setSelectedTraceId,
    selectedWorkerId, setSelectedWorkerId,
    
    // Replay integration
    replayMode,
    replayEvents,
    replayIndex,
    replayPlaying,
    replaySpeed,
    setReplaySpeed,
    replayAnalysis,
    replayError,
    replayLoading,
    startReplay,
    pauseReplay,
    seekReplay,
    stepForwardReplay,
    stepBackwardReplay,
    restartReplay,
    enterReplayMode,
    exitReplayMode
  } = usePipeline();

  const [searchQuery, setSearchQuery]       = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [levelFilter, setLevelFilter]       = useState('all');
  const [taskTypeFilter, setTaskTypeFilter]   = useState('all');
  const [autoScroll, setAutoScroll]         = useState(true);
  const [paused, setPaused]                 = useState(false);
  const [newEventCount, setNewEventCount]   = useState(0);

  const consoleEndRef = useRef(null);
  const containerRef  = useRef(null);
  const prevEventsLengthRef = useRef(events.length);

  // Debounce search query
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchQuery);
    }, 150);
    return () => clearTimeout(handler);
  }, [searchQuery]);

  // Reset new event count when auto-scrolling is active or user reaches bottom
  useEffect(() => {
    if (autoScroll && !paused) {
      setNewEventCount(0);
    }
  }, [autoScroll, paused]);

  // Track new incoming events while paused to increment counter
  useEffect(() => {
    if (events.length > prevEventsLengthRef.current) {
      if (paused) {
        const added = events.length - prevEventsLengthRef.current;
        setNewEventCount(prev => prev + added);
      }
    }
    prevEventsLengthRef.current = events.length;
  }, [events, paused]);

  // Compute unique task types dynamically from current events array
  const taskTypeOptions = useMemo(() => {
    const activeEvents = replayMode ? replayEvents : events;
    const types = new Set(activeEvents.map(e => e.task_type).filter(Boolean));
    return ['all', ...Array.from(types)].sort();
  }, [events, replayMode, replayEvents]);

  const filteredEvents = useMemo(() => {
    const activeEvents = replayMode ? replayEvents : events;
    let result = activeEvents;
    if (levelFilter !== 'all') {
      result = result.filter(e => e.level === levelFilter.toUpperCase());
    }
    if (taskTypeFilter !== 'all') {
      result = result.filter(e => e.task_type === taskTypeFilter);
    }
    if (debouncedSearch) {
      const q = debouncedSearch.toLowerCase();
      result = result.filter(e =>
        e.event_type?.toLowerCase().includes(q) ||
        e.task_type?.toLowerCase().includes(q) ||
        e.worker_id?.toLowerCase().includes(q) ||
        e.message?.toLowerCase().includes(q)
      );
    }
    return result;
  }, [events, replayMode, replayEvents, levelFilter, taskTypeFilter, debouncedSearch]);

  // Virtualized/windowed events slice around replayIndex
  const slicedEvents = useMemo(() => {
    if (!replayMode) return filteredEvents;
    const startIdx = Math.max(0, replayIndex - 100);
    const endIdx = Math.min(filteredEvents.length, replayIndex + 101);
    return filteredEvents.slice(startIdx, endIdx);
  }, [replayMode, filteredEvents, replayIndex]);

  // Auto scroll effect (paused during replayMode)
  useEffect(() => {
    if (replayMode) return;
    if (autoScroll && !paused) {
      consoleEndRef.current?.scrollIntoView?.({ behavior: 'smooth' });
    }
  }, [filteredEvents, autoScroll, paused, replayMode]);

  const handleScroll = useCallback(() => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 50;
    if (isNearBottom) {
      setPaused(false);
      setNewEventCount(0);
    } else {
      setPaused(true);
    }
  }, []);

  const handleJumpToLatest = () => {
    setPaused(false);
    setNewEventCount(0);
    consoleEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    consoleEndRef.current?.focus();
  };

  const handleCopy = () => {
    const text = filteredEvents.map(l => 
      `[${l.rawTimestamp || 'Not Available'}] [${l.level}] [${l.worker_id}] [${l.task_type}] ${l.event_type}: ${l.message}`
    ).join('\n');
    
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text).catch(() => {
        alert("Clipboard copy failed. Try downloading the file.");
      });
    } else {
      alert("Clipboard API not available. Try downloading the file.");
    }
  };

  const handleDownload = () => {
    const text = filteredEvents.map(l => 
      `[${l.rawTimestamp || 'Not Available'}] [${l.level}] [${l.worker_id}] [${l.task_type}] ${l.event_type}: ${l.message}`
    ).join('\n');
    
    const bom = '\uFEFF';
    const blob = new Blob([bom + text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    
    const dateStr = new Date().toISOString().replace(/[-:]/g, '').replace('T', '_').split('.')[0];
    const a = Object.assign(document.createElement('a'), {
      href: url,
      download: `scaleflow_pipeline_${events[0]?.pipeline_id || 'log'}_${dateStr}.txt`,
    });
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadJson = () => {
    const exportedEvents = filteredEvents.map(({ displayTime, ...rest }) => rest);
    const text = JSON.stringify(exportedEvents, null, 2);
    const blob = new Blob([text], { type: 'application/json;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    
    const dateStr = new Date().toISOString().replace(/[-:]/g, '').replace('T', '_').split('.')[0];
    const a = Object.assign(document.createElement('a'), {
      href: url,
      download: `scaleflow_pipeline_${events[0]?.pipeline_id || 'log'}_${dateStr}.json`,
    });
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleResetFilters = useCallback(() => {
    setSearchQuery('');
    setLevelFilter('all');
    setTaskTypeFilter('all');
  }, []);

  const controlBtnStyle = {
    background: 'rgba(255,255,255,0.04)',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: '4px',
    color: 'rgba(255,255,255,0.7)',
    fontSize: '10px',
    padding: '3px 8px',
    cursor: 'pointer',
    fontFamily: 'monospace',
    display: 'flex',
    alignItems: 'center',
    gap: '4px'
  };

  return (
    <div style={{
      background: '#070b14',
      border: '1px solid rgba(255,255,255,0.06)',
      borderRadius: '14px',
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column',
      boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
    }}>
      {/* Toolbar */}
      <ConsoleToolbar
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        levelFilter={levelFilter}
        onLevelFilterChange={setLevelFilter}
        taskTypeFilter={taskTypeFilter}
        onTaskTypeFilterChange={setTaskTypeFilter}
        taskTypeOptions={taskTypeOptions}
        autoScroll={autoScroll}
        onAutoScrollToggle={setAutoScroll}
        onCopy={handleCopy}
        onDownload={handleDownload}
        onResetFilters={handleResetFilters}
      />

      {/* Terminal title bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        padding: '8px 16px',
        background: 'rgba(255,255,255,0.02)',
        borderBottom: '1px solid rgba(255,255,255,0.04)',
      }}>
        {['#ef4444','#f59e0b','#10b981'].map(c => (
          <div key={c} style={{ width: 10, height: 10, borderRadius: '50%', background: c, opacity: 0.6 }} />
        ))}
        <span style={{ marginLeft: 8, fontSize: '10px', color: 'rgba(255,255,255,0.25)', fontFamily: 'monospace' }}>
          {replayMode ? 'scaleflow — execution replay viewer' : 'scaleflow — live backend execution log stream'}
        </span>

        <button
          onClick={replayMode ? exitReplayMode : enterReplayMode}
          disabled={replayLoading}
          style={{
            marginLeft: '12px',
            fontSize: '9px',
            color: '#a78bfa',
            background: 'rgba(167, 139, 250, 0.1)',
            border: '1px solid rgba(167, 139, 250, 0.2)',
            borderRadius: 4,
            padding: '1px 8px',
            cursor: 'pointer',
            fontWeight: 'bold',
            fontFamily: 'monospace'
          }}
        >
          {replayLoading ? 'LOADING...' : replayMode ? 'EXIT REPLAY' : 'ENTER REPLAY'}
        </button>

        {paused && newEventCount > 0 && !replayMode && (
          <button
            onClick={handleJumpToLatest}
            aria-label={`Jump to latest log entry, ${newEventCount} new events`}
            style={{
              marginLeft: 'auto',
              fontSize: '9px',
              color: '#3b82f6',
              background: 'rgba(59,130,246,0.1)',
              border: '1px solid rgba(59,130,246,0.2)',
              borderRadius: 4,
              padding: '1px 6px',
              cursor: 'pointer',
              fontFamily: 'monospace',
            }}
          >
            ⬇ {newEventCount} NEW EVENTS
          </button>
        )}
        {paused && newEventCount === 0 && !replayMode && (
          <span style={{
            marginLeft: 'auto',
            fontSize: '9px',
            color: '#f59e0b',
            background: 'rgba(245,158,11,0.1)',
            border: '1px solid rgba(245,158,11,0.2)',
            borderRadius: 4,
            padding: '1px 6px',
            fontFamily: 'monospace',
          }}>
            SCROLL PAUSED
          </span>
        )}
      </div>

      {/* Replay Mode Banner & RCA Summary */}
      {replayMode && (
        <div style={{
          background: 'rgba(167, 139, 250, 0.12)',
          borderBottom: '1px solid rgba(167, 139, 250, 0.25)',
          padding: '8px 16px',
          display: 'flex',
          flexDirection: 'column',
          gap: '4px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '11px', fontWeight: 'bold', color: '#a78bfa' }}>REPLAY MODE</span>
            <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.5)' }}>• Live updates paused • Viewing historical execution</span>
          </div>
          {replayAnalysis && (
            <div style={{ fontSize: '10.5px', color: 'rgba(255,255,255,0.7)', fontFamily: 'monospace', marginTop: '4px' }}>
              <strong>Root Cause Analysis:</strong> {replayAnalysis.root_cause} (Confidence: <span style={{ color: '#10b981', fontWeight: 'bold' }}>{replayAnalysis.confidence}</span>, Rule: <code>{replayAnalysis.rule}</code>)
            </div>
          )}
        </div>
      )}

      {/* Playback Controls */}
      {replayMode && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          padding: '8px 16px',
          background: 'rgba(255,255,255,0.01)',
          borderBottom: '1px solid rgba(255,255,255,0.04)',
          overflowX: 'auto'
        }}>
          <button onClick={restartReplay} style={controlBtnStyle}>↺ Restart</button>
          <button onClick={stepBackwardReplay} style={controlBtnStyle}>◀ Prev</button>
          <button onClick={replayPlaying ? pauseReplay : startReplay} style={{ ...controlBtnStyle, color: '#a78bfa', borderColor: 'rgba(167, 139, 250, 0.4)' }}>
            {replayPlaying ? '⏸ Pause' : '▶ Play'}
          </button>
          <button onClick={stepForwardReplay} style={controlBtnStyle}>Next ▶</button>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginLeft: '12px' }}>
            <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.4)', fontFamily: 'monospace' }}>SPEED:</span>
            {[0.5, 1, 2, 5].map((speed) => (
              <button
                key={speed}
                onClick={() => setReplaySpeed(speed)}
                style={{
                  ...controlBtnStyle,
                  background: replaySpeed === speed ? 'rgba(167, 139, 250, 0.2)' : 'transparent',
                  borderColor: replaySpeed === speed ? '#a78bfa' : 'rgba(255,255,255,0.1)',
                  color: replaySpeed === speed ? '#a78bfa' : 'rgba(255,255,255,0.5)'
                }}
              >
                {speed}x
              </button>
            ))}
          </div>

          <div style={{ marginLeft: 'auto', fontSize: '10px', color: 'rgba(255,255,255,0.3)', fontFamily: 'monospace' }}>
            EVENT {replayIndex + 1} / {replayEvents.length}
          </div>
        </div>
      )}

      {/* Log viewport */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        role="log"
        aria-live="polite"
        aria-label="Pipeline execution log"
        style={{
          height: 280,
          overflowY: 'auto',
          padding: '12px 18px',
          fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
          fontSize: '11.5px',
          lineHeight: 1.8,
          color: 'rgba(255,255,255,0.55)',
          display: 'flex',
          flexDirection: 'column',
          gap: 2,
        }}
        className="console-scrollbar"
      >
        {replayError || error ? (
          <div role="alert" style={{ color: '#ef4444', textAlign: 'center', marginTop: 60, fontSize: '12px' }}>
            Error: {replayError || error}
          </div>
        ) : (replayLoading || loading) && slicedEvents.length === 0 ? (
          <div role="status" style={{ color: 'rgba(255,255,255,0.2)', textAlign: 'center', marginTop: 60, fontSize: '12px' }}>
            Loading execution events...
          </div>
        ) : slicedEvents.length === 0 ? (
          <div role="status" style={{ color: 'rgba(255,255,255,0.2)', textAlign: 'center', marginTop: 60, fontSize: '12px' }}>
            No execution events have been recorded for this pipeline.
          </div>
        ) : (
          slicedEvents.map((log) => {
            if (log.id === null || log.id === undefined) return null;
            const key = `${log.source || 'task_log'}-${log.id}`;
            const globalIdx = filteredEvents.indexOf(log);
            const isReplayActiveEvent = replayMode && globalIdx === replayIndex;

            const isSelected = (log.task_id && log.task_id === selectedTaskId) ||
                               (log.correlation_id && log.correlation_id === selectedTraceId) ||
                               (log.worker_id && log.worker_id !== 'system' && log.worker_id === selectedWorkerId);
            
            const handleRowClick = () => {
              if (replayMode) {
                seekReplay(globalIdx);
              } else {
                if (isSelected) {
                  setSelectedTaskId(null);
                  setSelectedTraceId(null);
                  setSelectedWorkerId(null);
                } else {
                  setSelectedTaskId(log.task_id || null);
                  setSelectedTraceId(log.correlation_id || null);
                  setSelectedWorkerId((log.worker_id && log.worker_id !== 'system') ? log.worker_id : null);
                }
              }
            };
            
            return (
              <LogRow
                key={key}
                log={log}
                isSelected={isSelected}
                isReplayActiveEvent={isReplayActiveEvent}
                onClick={handleRowClick}
              />
            );
          })
        )}
        <div ref={consoleEndRef} tabIndex={-1} style={{ outline: 'none' }} />
      </div>

      {/* Secondary JSON Download Action */}
      <div style={{ padding: '4px 16px', display: 'flex', justifyContent: 'flex-end', background: 'rgba(0,0,0,0.1)' }}>
        <button
          onClick={handleDownloadJson}
          aria-label="Download logs as JSON"
          style={{ background: 'none', border: 'none', color: 'rgba(255,255,255,0.3)', cursor: 'pointer', fontSize: '9px', fontFamily: 'monospace' }}
        >
          [DOWNLOAD JSON]
        </button>
      </div>

      <style>{`
        @keyframes fadeInLog {
          from { opacity: 0; transform: translateY(3px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        .console-scrollbar::-webkit-scrollbar { width: 5px; }
        .console-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .console-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(255,255,255,0.08);
          border-radius: 3px;
        }
        .console-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(255,255,255,0.15);
        }
        .log-row-hover:hover {
          background: rgba(255,255,255,0.04) !important;
        }
      `}</style>
    </div>
  );
};

export default ExecutionConsole;
