import React from 'react';
import Card from '../../ui/Card';
import ClusterMetrics from './ClusterMetrics';
import QueueMetrics from './QueueMetrics';
import useMetrics from './useMetrics';

/**
 * Pluggable MetricsCard rendering a list of system widgets.
 */
export const MetricsCard = () => {
  const metrics = useMetrics();

  // Widget registry list to render metrics in pluggable sections
  const widgets = [
    {
      id: 'cluster',
      Component: ClusterMetrics,
      props: {
        redisStatus: metrics.redisStatus,
        dbStatus: metrics.dbStatus,
        qdrantStatus: metrics.qdrantStatus,
        leaderId: metrics.leaderId,
        orchestratorCount: metrics.orchestratorCount
      }
    },
    {
      id: 'queue',
      Component: QueueMetrics,
      props: {
        totalQueueSize: metrics.totalQueueSize,
        queuePressure: metrics.queuePressure,
        activeWorkersCount: metrics.activeWorkersCount
      }
    }
  ];

  return (
    <Card 
      className="metrics-card-panel"
      header={<span className="text-h4" style={{ color: 'var(--text-primary)' }}>3. Telemetry Indicators</span>}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-20)' }}>
        {widgets.map(({ id, Component, props }, index) => (
          <React.Fragment key={id}>
            <Component {...props} />
            {index < widgets.length - 1 && (
              <hr style={{ border: 'none', borderTop: '1px solid var(--border-divider)', margin: 0 }} />
            )}
          </React.Fragment>
        ))}
      </div>
    </Card>
  );
};
export default MetricsCard;
