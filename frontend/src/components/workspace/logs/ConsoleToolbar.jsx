import React from 'react';
import { Search, Copy, Download, Trash2 } from 'lucide-react';

export const ConsoleToolbar = ({ searchQuery, onSearchChange, levelFilter, onLevelFilterChange, autoScroll, onAutoScrollToggle, onCopy, onDownload, onClear }) => {
  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: '12px',
        alignItems: 'center',
        padding: '10px var(--spacing-16)',
        backgroundColor: 'rgba(0,0,0,0.3)',
        borderBottom: '1px solid var(--border-subtle)',
        fontFamily: 'var(--font-mono)',
        fontSize: '11px',
      }}
    >
      {/* Search Input */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-6)', padding: '2px 8px', backgroundColor: 'rgba(0,0,0,0.2)', width: '160px' }}>
        <Search size={12} style={{ color: 'var(--text-muted)' }} />
        <input
          type="text"
          placeholder="Filter logs..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          style={{ background: 'none', border: 'none', color: 'var(--text-primary)', outline: 'none', width: '100%', fontSize: '10.5px' }}
        />
      </div>

      {/* Level Filter */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        <span style={{ color: 'var(--text-muted)' }}>LEVEL:</span>
        <select
          value={levelFilter}
          onChange={(e) => onLevelFilterChange(e.target.value)}
          style={{
            backgroundColor: 'rgba(0,0,0,0.3)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-6)',
            color: 'var(--text-primary)',
            padding: '2px 6px',
            outline: 'none',
            fontSize: '10px',
            fontFamily: 'var(--font-mono)',
          }}
        >
          <option value="all">ALL</option>
          <option value="info">INFO</option>
          <option value="success">SUCCESS</option>
          <option value="warning">WARNING</option>
          <option value="error">ERROR</option>
        </select>
      </div>

      {/* Auto Scroll Toggle */}
      <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', color: 'var(--text-secondary)', marginLeft: '8px' }}>
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
        {/* Copy */}
        <button
          onClick={onCopy}
          style={{ display: 'flex', alignItems: 'center', gap: '4px', background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', padding: '4px' }}
          title="Copy to clipboard"
        >
          <Copy size={12} /> COPY
        </button>

        {/* Download */}
        <button
          onClick={onDownload}
          style={{ display: 'flex', alignItems: 'center', gap: '4px', background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', padding: '4px' }}
          title="Download log file"
        >
          <Download size={12} /> DOWNLOAD
        </button>

        {/* Clear */}
        <button
          onClick={onClear}
          style={{ display: 'flex', alignItems: 'center', gap: '4px', background: 'none', border: 'none', color: 'var(--color-failure)', cursor: 'pointer', padding: '4px' }}
          title="Clear screen"
        >
          <Trash2 size={12} /> CLEAR
        </button>
      </div>
    </div>
  );
};
export default ConsoleToolbar;
