import React, { useState } from 'react';
import Card from '../Card';
import Panel from '../Panel';
import Stack from '../Stack';
import Grid from '../Grid';
import Modal from '../Modal';
import Button from '../Button';
import ConfirmDialog from '../ConfirmDialog';

export const LayoutsShowcase = () => {
  const [modalOpen, setModalOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  return (
    <div className="showcase-section" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <h3 className="text-h3" style={{ borderBottom: '1px solid var(--border-subtle)', paddingBottom: '8px' }}>Layout Primitives & Dialogs</h3>

      <Grid cols={3} gap="20">
        <Card header={<span className="text-h4">Ingestion Card</span>} footer={<span className="text-caption">Footer info</span>}>
          <p className="text-body" style={{ color: 'var(--text-secondary)' }}>
            This represents atomic card containers.
          </p>
        </Card>
        
        <Panel>
          <span className="text-h4" style={{ display: 'block', marginBottom: '8px' }}>Raw Panel Block</span>
          <p className="text-body" style={{ color: 'var(--text-secondary)' }}>
            Panel wrappers with standard borders and background configurations.
          </p>
        </Panel>

        <Card header={<span className="text-h4">Interactive Dialogs</span>}>
          <Stack gap="8">
            <Button variant="primary" onClick={() => setModalOpen(true)}>Open Details Modal</Button>
            <Button variant="danger" onClick={() => setConfirmOpen(true)}>Open Confirm Modal</Button>
          </Stack>
        </Card>
      </Grid>

      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title="Cluster Resource Allocation Details">
        <p className="text-body" style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>
          This dialog displays deep details regarding active processing limits, cluster partitions, and task worker availability records.
        </p>
        <Button variant="secondary" onClick={() => setModalOpen(false)}>Close Window</Button>
      </Modal>

      <ConfirmDialog
        isOpen={confirmOpen}
        title="Destroy Execution Worker Node?"
        message="This action will force disconnect worker instance 'host-node-7b'. All executing subtasks will be rescheduled. This action cannot be undone."
        confirmText="Confirm Terminate"
        variant="danger"
        onConfirm={() => setConfirmOpen(false)}
        onCancel={() => setConfirmOpen(false)}
      />
    </div>
  );
};
export default LayoutsShowcase;
