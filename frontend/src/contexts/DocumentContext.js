import React, { createContext, useState, useContext } from 'react';

const DocumentContext = createContext(null);

export const DocumentProvider = ({ children }) => {
  const [selectedDocumentId, setSelectedDocumentId] = useState(null);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [fileType, setFileType] = useState('document_processing_demo');
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState('');

  return (
    <DocumentContext.Provider value={{
      selectedDocumentId,
      setSelectedDocumentId,
      uploadedFiles,
      setUploadedFiles,
      fileType,
      setFileType,
      uploading,
      setUploading,
      uploadStatus,
      setUploadStatus
    }}>
      {children}
    </DocumentContext.Provider>
  );
};

export const useDocument = () => {
  const context = useContext(DocumentContext);
  if (!context) {
    throw new Error('useDocument must be used within a DocumentProvider');
  }
  return context;
};
