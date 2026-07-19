import React from 'react';
import useUpload from './useUpload';
import UploadCardView from './UploadCardView';

/**
 * Container component managing document ingestion logic.
 */
export const UploadCard = () => {
  const {
    fileType,
    setFileType,
    uploading,
    uploadStatus,
    uploadFile,
    dragActive,
    setDragActive
  } = useUpload();

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      uploadFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      uploadFile(e.target.files[0]);
    }
  };

  return (
    <UploadCardView
      fileType={fileType}
      setFileType={setFileType}
      uploading={uploading}
      uploadStatus={uploadStatus}
      dragActive={dragActive}
      onDragEnter={handleDrag}
      onDragLeave={handleDrag}
      onDrop={handleDrop}
      onFileChange={handleFileChange}
    />
  );
};
export default UploadCard;
