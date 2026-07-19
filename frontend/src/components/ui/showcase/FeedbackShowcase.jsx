import React, { useState } from 'react';
import Badge from '../Badge';
import StatusBadge from '../StatusBadge';
import Alert from '../Alert';
import Toast from '../Toast';
import Spinner from '../Spinner';
import Skeleton from '../Skeleton';
import ProgressBar from '../ProgressBar';

export const FeedbackShowcase = () => {
  const [toastActive, setToastActive] = useState(true);

  return (
    <div className="showcase-section" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <h3 className="text-h3" style={{ borderBottom: '1px solid var(--border-subtle)', paddingBottom: '8px' }}>Feedback & Banners</h3>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <h4 className="text-h4">Status Badges & Tags</h4>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <Badge variant="success">Completed</Badge>
          <Badge variant="warning">Retrying</Badge>
          <Badge variant="danger">Failed</Badge>
          <Badge variant="info">Queued</Badge>

          <span style={{ margin: '0 12px', color: 'var(--border-divider)' }}>|</span>

          <StatusBadge status="online">Active Node</StatusBadge>
          <StatusBadge status="offline">Offline Host</StatusBadge>
          <StatusBadge status="checking">Provisioning</StatusBadge>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <h4 className="text-h4">Alert Cards</h4>
        <Alert variant="info" title="System Notice">
          Orchestration engines will undergo background updates at 03:00 UTC.
        </Alert>
        <Alert variant="warning" title="Orchestration Health">
          Node latency exceeded SLA limits. Task executions are currently deferred.
        </Alert>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <h4 className="text-h4">Load State Placeholders</h4>
        <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
          <Spinner size="md" />
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <Skeleton variant="text" width="60%" />
            <Skeleton variant="rect" height="40px" />
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <h4 className="text-h4">ProgressBar Percentage</h4>
        <ProgressBar value={72} variant="primary" />
        <ProgressBar value={100} variant="success" />
      </div>

      {toastActive && (
        <div style={{ position: 'fixed', bottom: '20px', right: '20px', zIndex: 'var(--z-index-toast)' }}>
          <Toast
            variant="success"
            message="Cluster sync successful!"
            onClose={() => setToastActive(false)}
          />
        </div>
      )}
    </div>
  );
};
export default FeedbackShowcase;
