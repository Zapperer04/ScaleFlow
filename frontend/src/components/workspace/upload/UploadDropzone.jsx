import React, { useState, useRef } from 'react';
import { UploadCloud, AlertTriangle, FileText } from 'lucide-react';

export const UploadDropzone = ({ onUploadStart, maxSizeBytes = 100 * 1024 * 1024 }) => {
  const [dragActive, setDragActive]       = useState(false);
  const [validationError, setValidationError] = useState('');
  const [selectedFile, setSelectedFile]   = useState(null);
  const [uploading, setUploading]         = useState(false);
  const fileInputRef = useRef(null);

  const formatSize = (bytes) => {
    if (!bytes) return '0 B';
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
  };

  const validateAndProcess = (file) => {
    setValidationError('');
    if (!file) return;
    if (file.type !== 'application/pdf') {
      setValidationError('Only PDF documents are supported.');
      return;
    }
    if (file.size > maxSizeBytes) {
      setValidationError(`File exceeds the ${formatSize(maxSizeBytes)} limit.`);
      return;
    }
    setSelectedFile(file);
    setUploading(true);
    onUploadStart(file);
  };

  const handleDrag = (e) => {
    e.preventDefault(); e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') setDragActive(true);
    else if (e.type === 'dragleave') setDragActive(false);
  };

  const handleDrop = (e) => {
    e.preventDefault(); e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files?.[0]) validateAndProcess(e.dataTransfer.files[0]);
  };

  const handleChange = (e) => {
    e.preventDefault();
    if (e.target.files?.[0]) validateAndProcess(e.target.files[0]);
  };

  return (
    <div style={{ position: 'relative' }}>
      <div
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        onClick={() => !uploading && fileInputRef.current?.click()}
        style={{
          border: dragActive
            ? '2px dashed #3b82f6'
            : validationError
            ? '2px dashed #ef4444'
            : '2px dashed rgba(255,255,255,0.1)',
          borderRadius: '16px',
          padding: '56px 32px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '16px',
          background: dragActive
            ? 'rgba(59, 130, 246, 0.05)'
            : 'rgba(255,255,255,0.01)',
          cursor: uploading ? 'default' : 'pointer',
          transition: 'all 0.25s ease',
          textAlign: 'center',
          minHeight: '240px',
          backdropFilter: 'blur(8px)',
        }}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,application/pdf"
          style={{ display: 'none' }}
          onChange={handleChange}
        />

        {/* Icon area */}
        {uploading ? (
          <div style={{
            width: 64,
            height: 64,
            borderRadius: '50%',
            background: 'rgba(59, 130, 246, 0.1)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            animation: 'iconPop 0.3s ease',
          }}>
            <FileText size={28} style={{ color: '#3b82f6' }} />
          </div>
        ) : (
          <div style={{
            width: 64,
            height: 64,
            borderRadius: '50%',
            background: dragActive ? 'rgba(59, 130, 246, 0.12)' : 'rgba(255,255,255,0.04)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.25s',
            animation: dragActive ? 'bounce 0.5s ease infinite alternate' : 'none',
          }}>
            <UploadCloud size={28} style={{ color: dragActive ? '#3b82f6' : 'rgba(255,255,255,0.4)' }} />
          </div>
        )}

        {/* Labels */}
        {uploading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#3b82f6', animation: 'blink 1s ease infinite' }} />
              <span style={{ fontSize: '0.95rem', fontWeight: 700, color: '#fff' }}>
                {selectedFile?.name}
              </span>
            </div>
            <span style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.4)', fontFamily: 'monospace' }}>
              {formatSize(selectedFile?.size)} — uploading…
            </span>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, alignItems: 'center' }}>
            <span style={{ fontSize: '1rem', fontWeight: 700, color: dragActive ? '#fff' : 'rgba(255,255,255,0.85)' }}>
              {dragActive ? 'Release to Upload' : 'Drag & Drop PDF here'}
            </span>
            <span style={{ fontSize: '0.82rem', color: 'rgba(255,255,255,0.35)' }}>
              or <span style={{ color: '#3b82f6', fontWeight: 600 }}>browse files</span>
            </span>
          </div>
        )}

        {/* Constraints */}
        {!uploading && (
          <div style={{ display: 'flex', gap: 16, marginTop: 4 }}>
            {[`PDF only`, `Max ${formatSize(maxSizeBytes)}`].map(label => (
              <span key={label} style={{
                fontSize: '10px',
                color: 'rgba(255,255,255,0.25)',
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(255,255,255,0.06)',
                borderRadius: 20,
                padding: '3px 10px',
              }}>
                {label}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Validation error toast */}
      {validationError && (
        <div style={{
          position: 'absolute',
          bottom: -48,
          left: 0,
          right: 0,
          padding: '10px 16px',
          background: 'rgba(239, 68, 68, 0.08)',
          border: '1px solid rgba(239, 68, 68, 0.3)',
          borderRadius: 8,
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          color: '#ef4444',
          fontSize: '12px',
          animation: 'slideUp 0.2s ease',
        }}>
          <AlertTriangle size={14} />
          {validationError}
        </div>
      )}

      <style>{`
        @keyframes bounce {
          from { transform: translateY(0); }
          to   { transform: translateY(-5px); }
        }
        @keyframes blink {
          0%, 100% { opacity: 1; } 50% { opacity: 0.3; }
        }
        @keyframes iconPop {
          from { transform: scale(0.8); opacity: 0; }
          to   { transform: scale(1); opacity: 1; }
        }
        @keyframes slideUp {
          from { opacity: 0; transform: translateY(6px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
};

export default UploadDropzone;
