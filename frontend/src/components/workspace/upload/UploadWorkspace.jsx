import React, { useState } from 'react';
import { FileText, Upload, MessageSquare, Activity } from 'lucide-react';
import { UploadDropzone } from './UploadDropzone';
import { apiClient } from '../../../services/apiClient';

/**
 * WORKSPACE_EMPTY — Upload State
 *
 * The only primary action is uploading a PDF.
 * Chat, Pipeline, PDF Viewer, and all diagnostics are completely hidden.
 * Renders a drag-and-drop zone plus a recent documents library.
 *
 * Upload flow:
 *   Idle → Validating → Queued → Processing (auto-transition to WORKSPACE_PROCESSING)
 */
export const UploadWorkspace = ({
  uploadedFiles = [],
  onSelectDocument,
  onUploadComplete,
  onOpenChat,
  onInspectPipeline,
}) => {
  // Upload lifecycle states
  const [uploadPhase, setUploadPhase] = useState('idle'); // 'idle' | 'validating' | 'queued' | 'uploading' | 'error'
  const [uploadError, setUploadError] = useState('');
  const [isUploading, setIsUploading] = useState(false);

  const handleUploadStart = async (file) => {
    if (isUploading) return; // prevent concurrent uploads
    setIsUploading(true);
    setUploadError('');
    setUploadPhase('validating');

    try {
      // Brief validation phase UX
      await new Promise((r) => setTimeout(r, 400));
      setUploadPhase('queued');

      // Build multipart form data
      const formData = new FormData();
      formData.append('file', file);
      setUploadPhase('uploading');

      const res = await apiClient.post('/files/upload', formData);

      const { file_id, pipeline_id } = res.data;
      const detailResponse = await apiClient.get(`/files/${file_id}`);
      const fileRecord = detailResponse.data?.file || detailResponse.data;

      const normalizedDoc = {
        id:                file_id,
        pipeline_id:       pipeline_id,
        original_filename: fileRecord.original_filename,
        size_bytes:        fileRecord.size_bytes,
        file_size:         fileRecord.size_bytes,
        page_count:        fileRecord.page_count || null,
        status:            fileRecord.status,
        file_type:         fileRecord.file_type,
        created_at:        fileRecord.created_at,
        storage_uri:       fileRecord.storage_uri,
      };

      // Signal parent to transition to WORKSPACE_PROCESSING
      if (onUploadComplete) onUploadComplete(normalizedDoc);
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        err?.response?.data?.error ||
        err?.message ||
        'Upload failed. Please try again.';
      setUploadError(msg);
      setUploadPhase('error');
      setIsUploading(false);
    }
  };

  const recentDocs = (uploadedFiles || []).slice(0, 5);

  const phaseLabel = {
    idle: null,
    validating: 'Validating file...',
    queued: 'Queued for upload...',
    uploading: 'Uploading to server...',
    error: null,
  }[uploadPhase];

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'flex-start',
        minHeight: '100%',
        padding: '64px 24px 40px',
        gap: '40px',
      }}
    >
      {/* Page heading */}
      <div style={{ textAlign: 'center', maxWidth: '560px' }}>
        <h1
          style={{
            margin: '0 0 8px 0',
            fontSize: '1.6rem',
            fontWeight: 800,
            letterSpacing: '-0.03em',
            color: 'var(--text-primary)',
          }}
        >
          Upload a Document
        </h1>
        <p
          style={{
            margin: 0,
            fontSize: '0.9rem',
            color: 'var(--text-muted)',
            lineHeight: 1.6,
          }}
        >
          Drop a PDF and ScaleFlow will automatically extract, index, and prepare
          it for AI&nbsp;Chat.
        </p>
      </div>

      {/* Drop zone */}
      <div style={{ width: '100%', maxWidth: '560px' }}>
        {uploadPhase === 'idle' || uploadPhase === 'error' ? (
          <UploadDropzone
            onUploadStart={handleUploadStart}
            maxSizeBytes={100 * 1024 * 1024}
          />
        ) : (
          /* Mid-upload progress card */
          <div
            style={{
              border: '2px dashed rgba(59,130,246,0.3)',
              borderRadius: '16px',
              padding: '56px 32px',
              textAlign: 'center',
              background: 'rgba(59,130,246,0.03)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '20px',
              minHeight: '240px',
              justifyContent: 'center',
            }}
          >
            {/* Animated spinner ring */}
            <div
              style={{
                width: 64,
                height: 64,
                borderRadius: '50%',
                border: '3px solid rgba(59,130,246,0.15)',
                borderTop: '3px solid #3b82f6',
                animation: 'uploadSpin 1s linear infinite',
              }}
            />
            <div>
              <div
                style={{
                  fontSize: '0.95rem',
                  fontWeight: 700,
                  color: '#fff',
                  marginBottom: 4,
                }}
              >
                {phaseLabel}
              </div>
              <div
                style={{
                  fontSize: '0.8rem',
                  color: 'rgba(255,255,255,0.35)',
                  fontFamily: 'monospace',
                }}
              >
                {uploadPhase === 'validating' && 'Checking file type and size'}
                {uploadPhase === 'queued' && 'Preparing upload request'}
                {uploadPhase === 'uploading' && 'Sending to backend — do not close this tab'}
              </div>
            </div>
            {/* Upload flow breadcrumb */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                fontSize: '10px',
                color: 'rgba(255,255,255,0.25)',
                fontFamily: 'monospace',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
              }}
            >
              {['Validating', 'Queued', 'Uploading'].map((step, idx) => {
                const phaseOrder = { validating: 0, queued: 1, uploading: 2 };
                const currentIdx = phaseOrder[uploadPhase] ?? -1;
                const active = idx === currentIdx;
                const done = idx < currentIdx;
                return (
                  <React.Fragment key={step}>
                    <span
                      style={{
                        color: done
                          ? 'var(--color-success)'
                          : active
                          ? '#3b82f6'
                          : 'rgba(255,255,255,0.2)',
                        fontWeight: active ? 700 : 400,
                      }}
                    >
                      {done ? '✓ ' : ''}{step}
                    </span>
                    {idx < 2 && (
                      <span style={{ color: 'rgba(255,255,255,0.1)' }}>›</span>
                    )}
                  </React.Fragment>
                );
              })}
            </div>
          </div>
        )}

        {/* Upload error message */}
        {uploadPhase === 'error' && uploadError && (
          <div
            style={{
              marginTop: 12,
              padding: '10px 16px',
              background: 'rgba(239,68,68,0.08)',
              border: '1px solid rgba(239,68,68,0.3)',
              borderRadius: 8,
              color: '#ef4444',
              fontSize: '13px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 8,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1 }}>
              <Upload size={14} />
              <span>{uploadError}</span>
            </div>
            <button
              onClick={() => {
                setUploadError('');
                setUploadPhase('idle');
              }}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#ef4444',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: 700,
                padding: '0 4px',
              }}
              title="Dismiss error"
            >
              ✕
            </button>
          </div>
        )}
      </div>

      {/* Recent Ingestion History */}
      {recentDocs.length > 0 && (
        <div style={{ width: '100%', maxWidth: '560px' }}>
          <div
            style={{
              fontSize: '11px',
              fontWeight: 700,
              color: 'rgba(255,255,255,0.3)',
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              marginBottom: '12px',
            }}
          >
            Recent Ingestion History
          </div>
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
            }}
          >
            {recentDocs.map((doc) => {
              const s = (doc.status || '').toLowerCase();
              const statusColor = (s === 'completed' || s === 'processed') 
                ? 'var(--color-success)' 
                : (s === 'failed' || s === 'blocked' || s === 'cancelled') 
                ? 'var(--color-failure)' 
                : 'var(--color-warning)';
              
              return (
                <div
                  key={doc.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '12px 16px',
                    background: 'rgba(255,255,255,0.02)',
                    border: '1px solid rgba(255,255,255,0.06)',
                    borderRadius: '10px',
                    gap: '12px'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1, minWidth: 0 }}>
                    <FileText
                      size={18}
                      style={{ color: 'var(--color-accent)', flexShrink: 0 }}
                    />
                    <div style={{ minWidth: 0, flex: 1 }}>
                      <div
                        style={{
                          fontSize: '0.85rem',
                          fontWeight: 600,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          color: '#fff',
                          marginBottom: '2px'
                        }}
                      >
                        {doc.original_filename}
                      </div>
                      <div style={{ display: 'flex', gap: '8px', fontSize: '11px', color: 'var(--text-disabled)' }}>
                        <span>{doc.size_bytes ? `${Math.round(doc.size_bytes / 1024)} KB` : '—'}</span>
                        <span>•</span>
                        <span>{doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleDateString() : '—'}</span>
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    {/* Status Badge */}
                    <span
                      style={{
                        fontSize: '10px',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        color: statusColor,
                        background: `${statusColor}15`,
                        border: `1px solid ${statusColor}30`,
                        borderRadius: '20px',
                        padding: '3px 8px',
                      }}
                    >
                      {doc.status}
                    </span>

                    {/* Action Buttons: 1) Open Chat, 2) Inspect Pipeline */}
                    {(() => {
                      const s = (doc.status || '').toLowerCase();
                      const isProcessed = s === 'completed' || s === 'processed';
                      const isProcessing = s === 'processing' || s === 'queued' || s === 'running';

                      return (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          {/* Button 1: Open Chat (Enabled ONLY if processed) */}
                          <button
                            disabled={!isProcessed}
                            onClick={() => {
                              if (isProcessed) {
                                if (onOpenChat) onOpenChat(doc);
                                else if (onSelectDocument) onSelectDocument(doc);
                              }
                            }}
                            style={{
                              background: isProcessed ? 'rgba(59,130,246,0.1)' : 'rgba(255,255,255,0.02)',
                              border: `1px solid ${isProcessed ? 'rgba(59,130,246,0.3)' : 'rgba(255,255,255,0.06)'}`,
                              borderRadius: '6px',
                              color: isProcessed ? '#3b82f6' : 'var(--text-disabled)',
                              padding: '5px 10px',
                              fontSize: '11px',
                              fontWeight: 600,
                              cursor: isProcessed ? 'pointer' : 'not-allowed',
                              opacity: isProcessed ? 1 : 0.45,
                              transition: 'all 0.15s',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '4px',
                            }}
                            title={
                              isProcessed
                                ? 'Open AI Chat for this document'
                                : isProcessing
                                ? 'Processing in progress... Chat will unlock once parsing completes'
                                : 'Chat unavailable for this document'
                            }
                          >
                            <MessageSquare size={12} />
                            <span>Open Chat</span>
                          </button>

                          {/* Button 2: Inspect Pipeline (ALWAYS active for all documents) */}
                          <button
                            onClick={() => {
                              if (onInspectPipeline) onInspectPipeline(doc);
                              else if (onSelectDocument) onSelectDocument(doc);
                            }}
                            style={{
                              background: 'rgba(255,255,255,0.04)',
                              border: '1px solid rgba(255,255,255,0.12)',
                              borderRadius: '6px',
                              color: 'var(--text-primary)',
                              padding: '5px 10px',
                              fontSize: '11px',
                              fontWeight: 600,
                              cursor: 'pointer',
                              transition: 'all 0.15s',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '4px',
                            }}
                            onMouseEnter={(e) => {
                              e.currentTarget.style.background = 'rgba(255,255,255,0.08)';
                              e.currentTarget.style.borderColor = 'rgba(255,255,255,0.2)';
                            }}
                            onMouseLeave={(e) => {
                              e.currentTarget.style.background = 'rgba(255,255,255,0.04)';
                              e.currentTarget.style.borderColor = 'rgba(255,255,255,0.12)';
                            }}
                            title="View real-time pipeline execution & RAG progress for this pipeline ID"
                          >
                            <Activity size={12} style={{ color: 'var(--color-accent)' }} />
                            <span>Inspect Pipeline</span>
                          </button>
                        </div>
                      );
                    })()}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Supported formats row */}
      <div
        style={{
          display: 'flex',
          gap: 8,
          flexWrap: 'wrap',
          justifyContent: 'center',
        }}
      >
        {['PDF', 'OCR Enabled', 'Max 100 MB', 'Single upload'].map((label) => (
          <span
            key={label}
            style={{
              fontSize: '11px',
              color: 'rgba(255,255,255,0.25)',
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.06)',
              borderRadius: 20,
              padding: '4px 12px',
            }}
          >
            {label}
          </span>
        ))}
      </div>

      <style>{`
        @keyframes uploadSpin {
          from { transform: rotate(0deg); }
          to   { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default UploadWorkspace;
