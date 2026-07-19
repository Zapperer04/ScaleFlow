import React from 'react';
import useWorkers from './workers/useWorkers';
import WorkerCard from './workers/WorkerCard';
import ConfirmDialog from './ui/ConfirmDialog';
import WorkspaceLayout from './workspace/WorkspaceLayout';
import WorkspaceGrid from './workspace/WorkspaceGrid';
import PageHeader from './ui/PageHeader';

/**
 * Pure declarative composition root for Workers Registry Page.
 */
export const WorkersPage = () => {
  const { data, actions } = useWorkers();

  return (
    <WorkspaceLayout>
      <ConfirmDialog
        isOpen={data.confirmState.isOpen}
        title={data.confirmState.title}
        message={data.confirmState.message}
        variant={data.confirmState.variant}
        onConfirm={data.confirmState.onConfirm}
        onCancel={() => actions.setConfirmState(prev => ({ ...prev, isOpen: false }))}
      />

      <PageHeader 
        title="Worker Registry & Load Balancer"
        subtitle="Manage distributed processing host threads, capability registers, and dynamic lease allocations."
      />

      <WorkspaceGrid cols={3}>
        {data.workers.map((worker) => (
          <WorkerCard
            key={worker.worker_id}
            worker={worker}
            onExecuteAction={actions.executeWorkerAction}
          />
        ))}
      </WorkspaceGrid>
    </WorkspaceLayout>
  );
};

export default WorkersPage;
