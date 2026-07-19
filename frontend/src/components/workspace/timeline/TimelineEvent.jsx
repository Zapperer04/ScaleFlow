import React from 'react';

/**
 * Presentational row component displaying a normalized timeline trace node.
 */
export const TimelineEvent = ({ event }) => {
  const isError = event.severity === 'error' || event.severity === 'failed' || event.type === 'error';
  const isWarning = event.severity === 'warning' || event.type === 'warning';
  
  const indicatorColor = isError ? 'var(--color-failure)' : isWarning ? 'var(--color-warning)' : 'var(--color-success)';

  return (
    <div style={{ display: 'flex', gap: 'var(--spacing-16)', paddingBottom: 'var(--spacing-16)' }}>
      {/* Node status dot and vertical connector */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <span 
          style={{ 
            width: '10px', 
            height: '10px', 
            borderRadius: '50%', 
            background: indicatorColor, 
            marginTop: '4px',
            boxShadow: `0 0 8px ${indicatorColor}`
          }} 
        />
        <div style={{ flex: 1, width: '2px', background: 'var(--border-divider)', marginTop: '4px' }} />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', flex: 1 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
          <span className="text-body" style={{ fontWeight: 'var(--font-weight-bold)', color: 'var(--text-primary)' }}>
            {event.title}
          </span>
          <span className="text-caption" style={{ color: 'var(--text-disabled)', fontFamily: 'var(--font-family-mono)' }}>
            {new Date(event.timestamp).toLocaleTimeString()}
          </span>
        </div>
        <p className="text-caption" style={{ margin: 0, color: 'var(--text-secondary)', lineHeight: '1.4' }}>
          {event.description}
        </p>
      </div>
    </div>
  );
};
export default TimelineEvent;
