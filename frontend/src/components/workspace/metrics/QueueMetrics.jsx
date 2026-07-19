import React from 'react';
import ProgressBar from '../../ui/ProgressBar';

/**
 * Queue capacity and system pressure visualization widget.
 */
export const QueueMetrics = ({ totalQueueSize, queuePressure, activeWorkersCount }) => {
  const pressureColor = 
    queuePressure > 60 ? 'var(--color-failure)' : 
    queuePressure > 30 ? 'var(--color-warning)' : 'var(--color-success)';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-12)' }}>
      <span className="text-caption" style={{ fontWeight: 'var(--font-weight-bold)', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
        Execution Queue Pressure
      </span>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <span className="text-h2" style={{ color: pressureColor, fontWeight: 'var(--font-weight-bold)' }}>
          {queuePressure}%
        </span>
        <span className="text-caption" style={{ color: 'var(--text-disabled)' }}>
          {totalQueueSize} tasks queued
        </span>
      </div>

      <ProgressBar 
        progress={queuePressure} 
        variant={queuePressure > 60 ? 'danger' : queuePressure > 30 ? 'warning' : 'success'} 
      />

      <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border-divider)', paddingTop: 'var(--spacing-8)', color: 'var(--text-secondary)' }} className="text-caption">
        <span>Active Workers: <strong>{activeWorkersCount} Online</strong></span>
        <span>Status: <strong>{queuePressure > 60 ? 'Backpressure' : 'Optimal'}</strong></span>
      </div>
    </div>
  );
};
export default QueueMetrics;
