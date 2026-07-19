import React from 'react';
import Card from '../../ui/Card';
import EmptyState from '../../ui/EmptyState';
import TimelineEvent from './TimelineEvent';
import useTimeline from './useTimeline';

/**
 * Log trace timeline widget showing live ingestion stages.
 */
export const ActivityTimeline = () => {
  const { events = [], loading } = useTimeline();

  return (
    <Card 
      className="activity-timeline-panel"
      header={<span className="text-h4" style={{ color: 'var(--text-primary)' }}>Ingestion Activity Log Traces</span>}
    >
      {events.length === 0 ? (
        <EmptyState 
          title="No Logs Available" 
          description={loading ? "Polling data..." : "Select an ingestion run from the Ingestion Registry to monitor system execution details."}
        />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-4)', maxHeight: '350px', overflowY: 'auto', paddingRight: 'var(--spacing-8)' }}>
          {events.map((event) => (
            <TimelineEvent key={event.id} event={event} />
          ))}
        </div>
      )}
    </Card>
  );
};
export default ActivityTimeline;
