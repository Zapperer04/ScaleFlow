import React from 'react';
import Breadcrumb from '../ui/Breadcrumb';
import PageHeader from '../ui/PageHeader';
import { useWorkspace } from '../../contexts/WorkspaceContext';
import { usePipeline } from '../../contexts/PipelineContext';

/**
 * Renders the top workspace sub-header with active object breadcrumbs.
 */
export const OverviewHeader = () => {
  const { selectedDocId, selectDocument } = useWorkspace();
  const { pipelines } = usePipeline();

  const activeDoc = pipelines.find(p => p.pipeline_id === selectedDocId);
  const activeDocName = activeDoc ? activeDoc.filename : null;

  const breadcrumbs = [
    { label: 'AI Document Workspace', onClick: () => selectDocument(null) }
  ];

  if (activeDocName) {
    breadcrumbs.push({ label: activeDocName });
  } else {
    breadcrumbs.push({ label: 'Overview' });
  }

  return (
    <div className="overview-header-wrapper" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-8)' }}>
      <Breadcrumb items={breadcrumbs} />
      <PageHeader
        title={activeDocName ? `Document: ${activeDocName}` : "AI Document Ingestion Workspace"}
        subtitle={activeDocName ? `Monitoring live pipeline execution traces for ingestion run #${selectedDocId}` : "Ingest documents, monitor parsing pipelines, and query vector retrieval indexes."}
      />
    </div>
  );
};
export default OverviewHeader;
