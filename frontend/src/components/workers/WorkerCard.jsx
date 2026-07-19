import React from 'react';
import Card from '../ui/Card';
import Badge from '../ui/Badge';
import ProgressBar from '../ui/ProgressBar';
import Button from '../ui/Button';

/**
 * Presentational card showing capacities and lifecycle triggers for one processing worker.
 */
export const WorkerCard = ({ worker, onExecuteAction }) => {
  const isOnline = worker.status !== 'offline';
  const isBusy = worker.status === 'busy';

  const getStatusVariant = () => {
    if (isBusy) return 'warning';
    if (isOnline) return 'success';
    return 'danger';
  };

  return (
    <Card
      className="worker-registry-card"
      header={
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
          <span className="text-body" style={{ fontWeight: 'var(--font-weight-bold)', color: 'var(--text-primary)' }}>
            {worker.worker_id}
          </span>
          <Badge variant={getStatusVariant()}>
            {worker.status.toUpperCase()}
          </Badge>
        </div>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-16)' }}>
        
        {/* Core telemetry meters */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-8)' }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }} className="text-caption">
              <span>CPU Core Ingestion Load</span>
              <strong>{worker.cpu}%</strong>
            </div>
            <ProgressBar progress={worker.cpu} variant={worker.cpu > 75 ? 'danger' : 'success'} />
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }} className="text-caption">
              <span>RAM In-Memory Heap Buffer</span>
              <strong>{worker.memory}%</strong>
            </div>
            <ProgressBar progress={worker.memory} variant={worker.memory > 75 ? 'danger' : 'info'} />
          </div>
        </div>

        {/* Task statistics */}
        <div 
          style={{ 
            display: 'grid', 
            gridTemplateColumns: '1fr 1fr', 
            gap: 'var(--spacing-8)',
            padding: 'var(--spacing-8)',
            background: 'var(--bg-input)',
            borderRadius: 'var(--radius-4)'
          }}
          className="text-caption"
        >
          <div>
            <span style={{ color: 'var(--text-disabled)' }}>Succeeded: </span>
            <strong style={{ color: 'var(--color-success)' }}>{worker.tasks_completed}</strong>
          </div>
          <div>
            <span style={{ color: 'var(--text-disabled)' }}>Failed: </span>
            <strong style={{ color: 'var(--color-failure)' }}>{worker.tasks_failed}</strong>
          </div>
        </div>

        {/* Capabilities Excerpts */}
        <div>
          <span className="text-caption" style={{ fontWeight: 'var(--font-weight-bold)', color: 'var(--text-secondary)' }}>
            Node Capabilities
          </span>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '4px' }}>
            {worker.capabilities.map((cap) => (
              <span 
                key={cap} 
                className="text-caption" 
                style={{ 
                  fontSize: '9px', 
                  padding: '2px 6px', 
                  background: 'var(--bg-hover)', 
                  borderRadius: '3px',
                  color: 'var(--text-secondary)'
                }}
              >
                {cap.replace('_', ' ')}
              </span>
            ))}
          </div>
        </div>

        {/* Action Toggles */}
        <div style={{ display: 'flex', gap: 'var(--spacing-12)', borderTop: '1px solid var(--border-divider)', paddingTop: 'var(--spacing-12)' }}>
          <Button
            variant="secondary"
            onClick={() => onExecuteAction(worker.worker_id, 'start')}
            disabled={isOnline}
            style={{ flex: 1, padding: '6px' }}
          >
            Start
          </Button>
          <Button
            variant="danger"
            onClick={() => onExecuteAction(worker.worker_id, 'kill')}
            disabled={!isOnline}
            style={{ flex: 1, padding: '6px' }}
          >
            Shutdown
          </Button>
        </div>

      </div>
    </Card>
  );
};
export default WorkerCard;
