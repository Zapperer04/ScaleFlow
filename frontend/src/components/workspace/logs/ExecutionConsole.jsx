import React, { useEffect, useRef, useState, useCallback } from 'react';
import ConsoleToolbar from './ConsoleToolbar';

const LEVEL_STYLE = {
  error:   { color: '#ef4444', label: 'ERR ' },
  warning: { color: '#f59e0b', label: 'WARN' },
  success: { color: '#10b981', label: 'OK  ' },
  info:    { color: '#3b82f6', label: 'INFO' },
};

const WorkerColors = ['#a78bfa', '#34d399', '#fbbf24', '#60a5fa', '#f472b6'];
const workerColor = (name = '') => WorkerColors[name.charCodeAt(name.length - 1) % WorkerColors.length];

export const ExecutionConsole = ({ logs = [] }) => {
  const [searchQuery, setSearchQuery]   = useState('');
  const [levelFilter, setLevelFilter]   = useState('all');
  const [autoScroll, setAutoScroll]     = useState(true);
  const [paused, setPaused]             = useState(false);
  const consoleEndRef = useRef(null);
  const containerRef  = useRef(null);

  const filteredLogs = logs.filter(log => {
    const matchSearch = searchQuery
      ? [log.message, log.stage, log.worker].some(v =>
          v?.toLowerCase().includes(searchQuery.toLowerCase())
        )
      : true;
    const matchLevel = levelFilter === 'all' || log.level?.toLowerCase() === levelFilter;
    return matchSearch && matchLevel;
  });

  useEffect(() => {
    if (autoScroll && !paused) {
      consoleEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll, paused]);

  const handleScroll = useCallback(() => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 48;
    if (!isNearBottom) setPaused(true);
    else setPaused(false);
  }, []);

  const handleCopy = () => {
    navigator.clipboard.writeText(
      filteredLogs.map(l =>
        `${l.timestamp} [${l.level?.toUpperCase()}] ${l.worker} — ${l.stage}: ${l.message}`
      ).join('\n')
    );
  };

  const handleDownload = () => {
    const text = filteredLogs.map(l =>
      `${l.timestamp} [${l.level?.toUpperCase()}] ${l.worker} — ${l.stage}: ${l.message}`
    ).join('\n');
    const a = Object.assign(document.createElement('a'), {
      href: URL.createObjectURL(new Blob([text], { type: 'text/plain' })),
      download: `pipeline_log_${Date.now()}.txt`,
    });
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const handleClear = () => { setSearchQuery(''); setLevelFilter('all'); };

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
        autoScroll={autoScroll}
        onAutoScrollToggle={setAutoScroll}
        onCopy={handleCopy}
        onDownload={handleDownload}
        onClear={handleClear}
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
          scaleflow — pipeline execution log
        </span>
        {paused && (
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

      {/* Log viewport */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        style={{
          height: 280,
          overflowY: 'auto',
          padding: '12px 18px',
          fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
          fontSize: '11.5px',
          lineHeight: 1.8,
          color: 'rgba(255,255,255,0.55)',
          display: 'flex',
          flexDirection: 'column',
          gap: 2,
        }}
        className="console-scrollbar"
      >
        {filteredLogs.length === 0 ? (
          <div style={{ color: 'rgba(255,255,255,0.2)', textAlign: 'center', marginTop: 60, fontSize: '12px' }}>
            — no log entries match active filters —
          </div>
        ) : filteredLogs.map((log, idx) => {
          const lKey = log.level?.toLowerCase() || 'info';
          const ls   = LEVEL_STYLE[lKey] || LEVEL_STYLE.info;
          const wc   = workerColor(log.worker || '');
          return (
            <div
              key={idx}
              style={{
                display: 'flex',
                gap: 10,
                alignItems: 'baseline',
                animation: 'fadeInLog 0.12s ease-out',
                padding: '1px 0',
                borderRadius: 3,
              }}
            >
              {/* Timestamp */}
              <span style={{ color: 'rgba(255,255,255,0.2)', fontSize: '10.5px', flexShrink: 0, userSelect: 'none' }}>
                {log.timestamp}
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
              <span style={{ color: wc, flexShrink: 0, fontSize: '10.5px' }}>
                [{log.worker}]
              </span>

              {/* Stage */}
              {log.stage && (
                <span style={{ color: 'rgba(255,255,255,0.35)', flexShrink: 0, fontSize: '10.5px' }}>
                  {log.stage}:
                </span>
              )}

              {/* Message */}
              <span style={{ color: 'rgba(255,255,255,0.7)', flex: 1, wordBreak: 'break-all' }}>
                {log.message}
              </span>
            </div>
          );
        })}
        <div ref={consoleEndRef} />
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
      `}</style>
    </div>
  );
};

export default ExecutionConsole;
