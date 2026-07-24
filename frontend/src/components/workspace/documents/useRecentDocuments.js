import { usePipeline } from '../../../contexts/PipelineContext';
import { useWorkspace } from '../../../contexts/WorkspaceContext';

/**
 * Custom hook to manage recently ingested files/pipelines and handle document selections.
 */
export const useRecentDocuments = () => {
  const { pipelines = [] } = usePipeline();
  const { selectedDocId, selectDocument } = useWorkspace();

  // Map pipelines representing processed documents
  const documents = pipelines.map(p => ({
    id: p.pipeline_id,
    filename: p.filename || `Pipeline #${p.pipeline_id}`,
    status: p.status,
    progress: p.progress && typeof p.progress === 'object' && p.progress.total > 0
      ? Math.round((p.progress.completed / p.progress.total) * 100)
      : (typeof p.progress === 'number' ? p.progress : 0),
    timestamp: p.created_at || new Date().toISOString()
  }));

  const handleSelectDocument = (docId) => {
    selectDocument(prevId => (prevId === docId ? null : docId));
  };

  return {
    documents,
    selectedDocId,
    handleSelectDocument
  };
};
export default useRecentDocuments;
