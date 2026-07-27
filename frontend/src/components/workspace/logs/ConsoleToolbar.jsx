import React from 'react';
import { Search, Copy, Download, Trash2, Filter } from 'lucide-react';

export const ConsoleToolbar = ({ 
  searchQuery, 
  onSearchChange, 
  levelFilter, 
  onLevelFilterChange, 
  taskTypeFilter,
  onTaskTypeFilterChange,
  taskTypeOptions = [],
  autoScroll, 
  onAutoScrollToggle, 
  onCopy, 
  onDownload, 
  onResetFilters 
}) => {
  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: '10px',
        alignItems: 'center',
        padding: '8px 16px',
        backgroundColor: 'rgba(0,0,0,0.3)',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: '11px',
      }}
    >
      {/* Search Input */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '6px', padding: '2px 8px', backgroundColor: 'rgba(0,0,0,0.2)', width: '150px' }}>
        <Search size={12} style={{ color: 'rgba(255,255,255,0.4)' }} />
        <input
          id="log-search"
          type="text"
          placeholder="Filter logs..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          aria-label="Search logs"
          style={{ background: 'none', border: 'none', color: '#fff', outline: 'none', width: '100%', fontSize: '10.5px' }}
        />
      </div>

      {/* Task Type Filter */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        <Filter size={11} style={{ color: 'rgba(255,255,255,0.4)' }} />
        <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: '10px' }}>TASK:</span>
        <select
          value={taskTypeFilter || 'all'}
          onChange={(e) => onTaskTypeFilterChange?.(e.target.value)}
          aria-label="Filter by task type"
          style={{
            backgroundColor: 'rgba(0,0,0,0.4)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '6px',
            color: '#fff',
            padding: '2px 6px',
            outline: 'none',
            fontSize: '10px',
            fontFamily: 'monospace',
          }}
        >
          {taskTypeOptions.map(opt => (
            <option key={opt} value={opt}>{opt.toUpperCase()}</option>
          ))}
        </select>
      </div>

      {/* Level Filter */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: '10px' }}>LEVEL:</span>
        <select
          value={levelFilter}
          onChange={(e) => onLevelFilterChange(e.target.value)}
          aria-label="Filter by severity"
          style={{
            backgroundColor: 'rgba(0,0,0,0.4)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '6px',
            color: '#fff',
            padding: '2px 6px',
            outline: 'none',
            fontSize: '10px',
            fontFamily: 'monospace',
          }}
        >
          <option value="all">ALL</option>
          <option value="info">INFO</option>
          <option value="warning">WARN</option>
          <option value="error">ERR</option>
        </select>
      </div>

      {/* Auto Scroll Toggle */}
      <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', color: 'rgba(255,255,255,0.5)', marginLeft: '4px', fontSize: '10px' }}>
        <input
          type="checkbox"
          checked={autoScroll}
          onChange={(e) => onAutoScrollToggle(e.target.checked)}
          style={{ cursor: 'pointer' }}
        />
        <span>AUTO-SCROLL</span>
      </label>

      {/* Actions */}
      <div style={{ display: 'flex', gap: '8px', marginLeft: 'auto' }}>
        <button
          onClick={onCopy}
          aria-label="Copy visible logs to clipboard"
          style={{ display: 'flex', alignItems: 'center', gap: '4px', background: 'none', border: 'none', color: 'rgba(255,255,255,0.5)', cursor: 'pointer', padding: '4px', fontSize: '10px' }}
          title="Copy to clipboard"
        >
          <Copy size={11} /> COPY
        </button>

        <button
          onClick={onDownload}
          aria-label="Download logs"
          style={{ display: 'flex', alignItems: 'center', gap: '4px', background: 'none', border: 'none', color: 'rgba(255,255,255,0.5)', cursor: 'pointer', padding: '4px', fontSize: '10px' }}
          title="Download log file"
        >
          <Download size={11} /> DOWNLOAD
        </button>

        <button
          onClick={onResetFilters}
          aria-label="Reset all log filters"
          style={{ display: 'flex', alignItems: 'center', gap: '4px', background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', padding: '4px', fontSize: '10px' }}
          title="Reset filters"
        >
          <Trash2 size={11} /> RESET FILTERS
        </button>
      </div>
    </div>
  );
};
export default ConsoleToolbar;
