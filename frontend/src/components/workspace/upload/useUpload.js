import { useState } from 'react';
import { useDocument } from '../../../contexts/DocumentContext';
import { useWorkspace } from '../../../contexts/WorkspaceContext';
import { usePipeline } from '../../../contexts/PipelineContext';
import { uploadFile as apiUploadFile } from '../../../services/api';
import { pollingManager } from '../../../services/pollingManager';

/**
 * Custom hook to handle file uploads and workspace context updates.
 */
export const useUpload = () => {
  const { fileType, setFileType, uploading, setUploading, uploadStatus, setUploadStatus } = useDocument();
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
      
      // Update contexts
      setSelectedPipelineId(res.pipeline_id);
      selectDocument(res.pipeline_id);
      
      // Trigger instant telemetry poll refresh
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
