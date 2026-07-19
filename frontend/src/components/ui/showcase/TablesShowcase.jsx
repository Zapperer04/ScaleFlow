import React from 'react';
import Table from '../Table';
import EmptyState from '../EmptyState';
import ErrorState from '../ErrorState';
import CodeBlock from '../CodeBlock';
import Metric from '../Metric';
import KeyValue from '../KeyValue';
import Grid from '../Grid';

export const TablesShowcase = () => {
  return (
    <div className="showcase-section" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <h3 className="text-h3" style={{ borderBottom: '1px solid var(--border-subtle)', paddingBottom: '8px' }}>Data Display & Tables</h3>

      <Grid cols={3} gap="16">
        <Metric label="Total Jobs Ingested" value="1,842" change={<span style={{ color: 'var(--color-success)' }}>+12%</span>} />
        <Metric label="Orchestration Latency" value="24ms" />
        <Metric label="CPU Node Usage" value="84%" change={<span style={{ color: 'var(--color-warning)' }}>Saturated</span>} />
      </Grid>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '20px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <h4 className="text-h4">Table Grid Primitives</h4>
          <Table headers={['Worker Node', 'Role ID', 'IP Address', 'Active Tasks']}>
            <tr>
              <td>worker-us-01</td>
              <td>Ingestion Lead</td>
              <td>10.0.1.41</td>
              <td>14 active</td>
            </tr>
            <tr>
              <td>worker-us-02</td>
              <td>Validator Node</td>
              <td>10.0.1.42</td>
              <td>0 active</td>
            </tr>
          </Table>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <h4 className="text-h4">Key Value Rows</h4>
          <div className="panel" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <KeyValue label="Database Engine" value="SQLite v3" />
            <KeyValue label="Redis Status" value="Online (Cluster Mode)" />
            <KeyValue label="Vector DB Provider" value="Qdrant Local Host" />
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', borderTop: '1px dashed var(--border-subtle)', paddingTop: '16px' }}>
        <EmptyState
          title="No pipelines registered"
          message="Upload a document configuration mapping file to initialize and watch live pipeline executions."
          icon={<span>📂</span>}
        />

        <ErrorState
          title="Connection to cluster failed"
          message="Failed to sync connection states from lead coordinator node. Reconnect attempt will occur shortly."
          onRetry={() => {}}
        />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <h4 className="text-h4">Syntax CodeBlock Display</h4>
        <CodeBlock code={`{\n  "cluster_id": "scaleflow-prod-01",\n  "active_workers": 12,\n  "orchestrator_status": "healthy"\n}`} />
      </div>
    </div>
  );
};
export default TablesShowcase;
