import React from 'react';
import Card from '../../ui/Card';
import Select from '../../ui/Select';
import Spinner from '../../ui/Spinner';
import Alert from '../../ui/Alert';

/**
 * Presentational view component for the UploadCard.
 */
export const UploadCardView = ({
  fileType,
  setFileType,
  uploading,
  uploadStatus,
  onFileChange,
  dragActive,
  onDragEnter,
  onDragLeave,
  onDrop
}) => {
  const fileOptions = [
    { value: 'document_processing_demo', label: 'RAG Text Chunking Ingestion' },
    { value: 'structured_data_parser', label: 'Structured JSON Parser Ingestion' },
    { value: 'multimodal_extractor', label: 'Multimodal Image-to-Text Ingestion' }
  ];

  return (
    <Card 
      className={`upload-card-panel ${dragActive ? 'drag-active' : ''}`}
      header={<span className="text-h4" style={{ color: 'var(--text-primary)' }}>1. Ingest Raw Document</span>}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-16)' }}>
        <Select
          label="Processing DAG Ingestion Target"
          value={fileType}
          options={fileOptions}
          onChange={(e) => setFileType(e.target.value)}
          disabled={uploading}
        />

        <div
          className="file-drop-zone"
          onDragEnter={onDragEnter}
          onDragOver={onDragEnter}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
          style={{
            border: '2px dashed var(--border-subtle)',
            borderRadius: 'var(--radius-6)',
            padding: 'var(--spacing-24)',
            textAlign: 'center',
            background: dragActive ? 'var(--bg-hover)' : 'var(--bg-input)',
            cursor: 'pointer',
            transition: 'var(--transition-fast-ease)',
            position: 'relative'
          }}
        >
          <input
            type="file"
            id="file-upload-input"
            style={{ display: 'none' }}
            onChange={onFileChange}
            disabled={uploading}
          />
          <label htmlFor="file-upload-input" style={{ cursor: 'pointer', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 'var(--spacing-8)' }}>
            <span style={{ fontSize: '24px' }}>📂</span>
            <span className="text-body" style={{ color: 'var(--text-primary)', fontWeight: 'var(--font-weight-medium)' }}>
              Drag & Drop file here or <span style={{ color: 'var(--color-accent)' }}>browse</span>
            </span>
            <span className="text-caption" style={{ color: 'var(--text-disabled)' }}>
              Supports PDF, TXT, JSON, DOCX up to 50MB
            </span>
          </label>
        </div>

        {uploading && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-12)', padding: 'var(--spacing-12)', background: 'var(--bg-hover)', borderRadius: 'var(--radius-4)' }}>
            <Spinner size="sm" />
            <span className="text-caption" style={{ color: 'var(--text-secondary)' }}>Ingestion running...</span>
          </div>
        )}

        {!uploading && uploadStatus && (
          <Alert 
            variant={uploadStatus.includes('failed') ? 'danger' : 'success'}
            title="Ingestion Status"
          >
            {uploadStatus}
          </Alert>
        )}
      </div>
    </Card>
  );
};
export default UploadCardView;
