import React from 'react';

/**
 * Cluster database and broker status indicator widget.
 */
export const ClusterMetrics = React.memo(({ redisStatus, dbStatus, qdrantStatus, leaderId, orchestratorCount }) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-12)' }}>
      <span className="text-caption" style={{ fontWeight: 'var(--font-weight-bold)', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
        Infrastructure Health
      </span>
      
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 'var(--spacing-8)' }}>
        <div style={{ padding: 'var(--spacing-8)', background: 'var(--bg-input)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-4)', textAlign: 'center' }}>
          <div className="text-caption" style={{ color: 'var(--text-disabled)' }}>Redis</div>
          <span className={`status-dot ${redisStatus}`} style={{ display: 'inline-block', margin: 'var(--spacing-4) auto 0 auto' }} />
        </div>
        <div style={{ padding: 'var(--spacing-8)', background: 'var(--bg-input)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-4)', textAlign: 'center' }}>
          <div className="text-caption" style={{ color: 'var(--text-disabled)' }}>Postgres</div>
          <span className={`status-dot ${dbStatus}`} style={{ display: 'inline-block', margin: 'var(--spacing-4) auto 0 auto' }} />
        </div>
        <div style={{ padding: 'var(--spacing-8)', background: 'var(--bg-input)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-4)', textAlign: 'center' }}>
          <div className="text-caption" style={{ color: 'var(--text-disabled)' }}>Qdrant</div>
          <span className={`status-dot ${qdrantStatus}`} style={{ display: 'inline-block', margin: 'var(--spacing-4) auto 0 auto' }} />
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border-divider)', paddingTop: 'var(--spacing-8)', color: 'var(--text-secondary)' }} className="text-caption">
        <span>HA Orchestrators: <strong>{orchestratorCount}</strong></span>
        <span>Role: <strong>{leaderId !== 'Checking...' && leaderId !== 'None' ? 'Leader' : 'Replica'}</strong></span>
      </div>
    </div>
  );
});
export default ClusterMetrics;
