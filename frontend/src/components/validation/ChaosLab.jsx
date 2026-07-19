import React from 'react';
import Card from '../ui/Card';
import Button from '../ui/Button';
import Grid from '../ui/Grid';
import { CHAOS_ACTIONS } from './useValidation';

/**
 * Presentational panel for injecting chaos events and triggering failovers.
 */
export const ChaosLab = ({
  pausedQueues = [],
  onExecuteChaos,
  onToggleQueue
}) => {
  const queues = [
    { name: 'task_queue_easy', label: 'Easy Tasks Queue' },
    { name: 'task_queue_medium', label: 'Medium Tasks Queue' },
    { name: 'task_queue_hard', label: 'Hard Tasks Queue' }
  ];

  return (
    <Card 
      className="chaos-lab-panel"
      header={<span className="text-h4" style={{ color: 'var(--text-primary)' }}>System Chaos & Load Injections</span>}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-20)' }}>
        
        {/* Dynamic Chaos Buttons */}
        <div>
          <span className="text-caption" style={{ fontWeight: 'var(--font-weight-bold)', color: 'var(--text-secondary)', textTransform: 'uppercase', display: 'block', marginBottom: 'var(--spacing-12)' }}>
            Injections Catalog
          </span>
          <Grid cols={2} gap="12">
            {Object.values(CHAOS_ACTIONS).map((action) => (
              <Button
                key={action.id}
                variant={action.severity === 'danger' ? 'danger' : 'primary'}
                onClick={() => onExecuteChaos(action.id)}
                style={{ width: '100%', justifyContent: 'flex-start', padding: 'var(--spacing-12)' }}
              >
                <div style={{ textAlign: 'left', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                  <span style={{ fontWeight: 'var(--font-weight-bold)' }}>{action.title}</span>
                  <span className="text-caption" style={{ opacity: 0.8, fontWeight: 'normal' }}>
                    Severity: {action.severity.toUpperCase()}
                  </span>
                </div>
              </Button>
            ))}
          </Grid>
        </div>

        <hr style={{ border: 'none', borderTop: '1px solid var(--border-divider)', margin: 0 }} />

        {/* Queues Locks / Pauses */}
        <div>
          <span className="text-caption" style={{ fontWeight: 'var(--font-weight-bold)', color: 'var(--text-secondary)', textTransform: 'uppercase', display: 'block', marginBottom: 'var(--spacing-12)' }}>
            Broker Queue Lock Controls
          </span>
          <Grid cols={3} gap="12">
            {queues.map((q) => {
              const isPaused = pausedQueues.includes(q.name);
              return (
                <div 
                  key={q.name}
                  style={{
                    padding: 'var(--spacing-12)',
                    borderRadius: 'var(--radius-4)',
                    border: '1px solid var(--border-subtle)',
                    background: 'var(--bg-input)',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: 'var(--spacing-8)',
                    textAlign: 'center'
                  }}
                >
                  <span className="text-caption" style={{ fontWeight: 'var(--font-weight-bold)', color: 'var(--text-primary)' }}>
                    {q.label}
                  </span>
                  <Button
                    variant={isPaused ? 'success' : 'warning'}
                    onClick={() => onToggleQueue(q.name, isPaused)}
                    style={{ width: '100%', padding: '6px var(--spacing-8)', fontSize: '11px' }}
                  >
                    {isPaused ? 'Resume Dispatch' : 'Pause Dispatch'}
                  </Button>
                </div>
              );
            })}
          </Grid>
        </div>

      </div>
    </Card>
  );
};
export default ChaosLab;
