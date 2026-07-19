import React from 'react';
import Card from '../ui/Card';
import Skeleton from '../ui/Skeleton';
import WorkspaceLayout from './WorkspaceLayout';
import WorkspaceGrid from './WorkspaceGrid';

/**
 * Renders a full-screen loading skeleton placeholder.
 */
export const WorkspaceSkeleton = () => {
  return (
    <WorkspaceLayout>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-8)' }}>
        <Skeleton width="180px" height="24px" />
        <Skeleton width="340px" height="16px" />
      </div>
      <WorkspaceGrid cols={3}>
        <Card header={<Skeleton width="120px" height="16px" />}>
          <Skeleton height="140px" />
        </Card>
        <Card header={<Skeleton width="120px" height="16px" />}>
          <Skeleton height="140px" />
        </Card>
        <Card header={<Skeleton width="120px" height="16px" />}>
          <Skeleton height="140px" />
        </Card>
      </WorkspaceGrid>
      <WorkspaceGrid cols={2}>
        <Card header={<Skeleton width="120px" height="16px" />}>
          <Skeleton height="200px" />
        </Card>
        <Card header={<Skeleton width="120px" height="16px" />}>
          <Skeleton height="200px" />
        </Card>
      </WorkspaceGrid>
    </WorkspaceLayout>
  );
};
export default WorkspaceSkeleton;
