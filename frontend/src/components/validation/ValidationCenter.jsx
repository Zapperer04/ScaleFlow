import React from 'react';
import Card from '../ui/Card';
import Badge from '../ui/Badge';
import Grid from '../ui/Grid';

/**
 * Presentational panel rendering validation database and broker status checks.
 */
export const ValidationCenter = ({ items = [] }) => {
  return (
    <Card 
      className="validation-center-panel"
      header={<span className="text-h4" style={{ color: 'var(--text-primary)' }}>System Verification Center</span>}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-16)' }}>
        <p className="text-body" style={{ color: 'var(--text-secondary)', margin: 0 }}>
          Live verification status of connected messaging brokers, databases, and vector layers.
        </p>

        <Grid cols={2} gap="16">
          {items.map((item) => {
            const isHealthy = item.status === 'healthy';
            return (
              <div 
                key={item.id}
                style={{
                  padding: 'var(--spacing-16)',
                  borderRadius: 'var(--radius-6)',
                  border: '1px solid var(--border-subtle)',
                  background: 'var(--bg-input)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 'var(--spacing-8)'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span className="text-body" style={{ fontWeight: 'var(--font-weight-bold)', color: 'var(--text-primary)' }}>
                    {item.title}
                  </span>
                  <Badge variant={isHealthy ? 'success' : 'danger'}>
                    {item.status.toUpperCase()}
                  </Badge>
                </div>
                <p className="text-caption" style={{ margin: 0, color: 'var(--text-disabled)' }}>
                  {item.description}
                </p>
              </div>
            );
          })}
        </Grid>
      </div>
    </Card>
  );
};
export default ValidationCenter;
