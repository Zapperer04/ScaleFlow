import { useState } from 'react';
import { useDocument } from '../../../contexts/DocumentContext';
import { useWorkspace } from '../../../contexts/WorkspaceContext';
import { usePipeline } from '../../../contexts/PipelineContext';
import { uploadFile as apiUploadFile } from '../../../services/api';
import { pollingManager } from '../../../services/pollingManager';

/**
 * Custom hook to handle file uploads and workspace context updates.
 *
 * Upload response shape (from documents.js uploadFile):
 *   { id: file_id, pipeline_id, original_filename, ... }
 *
 * After a successful upload we must set:
 *   - DocumentContext.selectedDocumentId  →  res.id  (the file_id)
 *   - PipelineContext.selectedPipelineId  →  res.pipeline_id
 *
 * Previously this called selectDocument(res.pipeline_id) which pushed the
 * pipeline_id into the document context, so WorkspaceHome's state machine
 * (which watches selectedDocumentId against uploadedFiles) never fired.
 */
export const useUpload = () => {
  const { fileType, setFileType, uploading, setUploading, uploadStatus, setUploadStatus, setSelectedDocumentId } = useDocument();
  const { selectDocument } = useWorkspace();
  const { setSelectedPipelineId } = usePipeline();
  const [dragActive, setDragActive] = useState(false);

  const uploadFile = async (file) => {
    if (!file) return;
    setUploading(true);
    setUploadStatus('Ingesting file to ScaleFlow...');
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('pipeline_type', fileType);

      const res = await apiUploadFile(formData);
      setUploadStatus(`Upload success! Started pipeline #${res.pipeline_id}`);
      
      // Update both contexts with correct IDs:
      // - selectedDocumentId must be the file_id so WorkspaceHome state machine finds it in uploadedFiles
      // - selectedPipelineId must be the pipeline_id for DAG/telemetry polling
      setSelectedDocumentId(res.id);
      setSelectedPipelineId(res.pipeline_id);
      selectDocument(res.id);
      
      // Trigger instant telemetry poll refresh so pipelines[] updates immediately
      pollingManager.triggerFastUpdate();
    } catch (err) {
      console.error('File upload failed:', err);
      setUploadStatus('Upload failed: ' + (err.response?.data?.error || err.message));
    } finally {
      setUploading(false);
    }
  };

  return {
    fileType,
    setFileType,
    uploading,
    uploadStatus,
    uploadFile,
    dragActive,
    setDragActive
  };
};
export default useUpload;
