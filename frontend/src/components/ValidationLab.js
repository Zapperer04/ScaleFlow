import React from 'react';
import useValidation from './validation/useValidation';
import ValidationCenter from './validation/ValidationCenter';
import ChaosLab from './validation/ChaosLab';
import SubprocessRunner from './validation/SubprocessRunner';
import RecentOperations from './validation/RecentOperations';
import ConfirmDialog from './ui/ConfirmDialog';
import WorkspaceLayout from './workspace/WorkspaceLayout';
import WorkspaceGrid from './workspace/WorkspaceGrid';
import Tabs from './ui/Tabs';

/**
 * Pure declarative composition root for Chaos Engineering & System Validation Lab.
 */
export const ValidationLab = () => {
  const { data, actions } = useValidation();

  const tabOptions = [
    { id: 'center', label: 'Verification Center' },
    { id: 'chaos', label: 'Chaos & Injections' },
    { id: 'results', label: 'Subprocess Suite' }
  ];

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

      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-16)' }}>
        <Tabs 
          tabs={tabOptions} 
          activeTab={data.selectedTest === 'results' ? 'results' : data.confirmState.isOpen ? 'chaos' : 'center'} 
          onChange={(tabId) => {
            if (tabId === 'results') {
              actions.setSelectedTest('validation');
            }
          }}
        />

        <WorkspaceGrid cols={1}>
          <ValidationCenter items={data.validationItems} />
          
          <ChaosLab 
            pausedQueues={data.pausedQueues}
            onExecuteChaos={actions.executeChaosAction}
            onToggleQueue={actions.toggleQueueState}
          />
          
          <SubprocessRunner
            selectedTest={data.selectedTest}
            onTestChange={actions.setSelectedTest}
            testStatus={data.testStatus}
            testLogs={data.testLogs}
            isRunningTest={data.isRunningTest}
            onRunTest={actions.runTest}
          />
        </WorkspaceGrid>

        <RecentOperations operationsLog={data.operationsLog} />
      </div>
    </WorkspaceLayout>
  );
};

export default ValidationLab;
