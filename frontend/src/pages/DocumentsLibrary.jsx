/* eslint-disable no-unused-vars */
import React, { useState, useEffect } from 'react';
import { 
  Upload, FileText, Trash2, RefreshCw, MessageSquare, ExternalLink, 
  Search, ArrowUpDown, ChevronRight, FileJson, CheckCircle2, AlertOctagon
} from 'lucide-react';
import { useDocument } from '../contexts/DocumentContext';
import { usePipeline } from '../contexts/PipelineContext';
import { useWorkspace } from '../contexts/WorkspaceContext';
import { fetchUploadedFiles, uploadFile } from '../services/documents';
import { createPipeline, fetchPipelines } from '../services/pipelines';
import Button from '../components/ui/Button';
import Badge from '../components/ui/Badge';

export const DocumentsLibrary = ({ onNavigateToView }) => {
  const { uploadedFiles, setUploadedFiles, setSelectedDocumentId } = useDocument();
  const { pipelines, setPipelines, setSelectedPipelineId } = usePipeline();
  const { selectDocument } = useWorkspace();

  // Local States
  const [selectedFileDetail, setSelectedFileDetail] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  // Poll files lists
  useEffect(() => {
    const updateLists = async () => {
      try {
        const filesList = await fetchUploadedFiles();
        setUploadedFiles(filesList || []);
        
        const pipelineList = await fetchPipelines();
        setPipelines(pipelineList || []);
      } catch (err) {
        console.error("Error refreshing files", err);
      }
    };
    updateLists();
    const interval = setInterval(updateLists, 5000);
    return () => clearInterval(interval);
  }, [setUploadedFiles, setPipelines]);

  // Drag and Drop Handlers
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      await handleUpload(e.dataTransfer.files[0]);
    }
  };

  const handleFileInput = async (e) => {
    if (e.target.files && e.target.files[0]) {
      await handleUpload(e.target.files[0]);
    }
  };

  const handleUpload = async (file) => {
    setIsUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("pipeline_type", "document_processing_demo");

    try {
      const res = await uploadFile(formData);
      // Refresh list
      const filesList = await fetchUploadedFiles();
      setUploadedFiles(filesList || []);
      
      // Auto select newly uploaded file
      const newFile = filesList.find(f => f.original_filename === file.name);
      if (newFile) {
        setSelectedFileDetail(newFile);
      }
    } catch (err) {
      console.error("Upload error", err);
    } finally {
      setIsUploading(false);
    }
  };

  // Launch workspace chat with selected document
  const handleChatDocument = (file) => {
    setSelectedDocumentId(file.id);
    selectDocument(file.id);
    
    // Associate active pipeline
    const assoc = pipelines.find(p => p.file_id === file.id || p.id === file.pipeline_id);
    if (assoc) {
      setSelectedPipelineId(assoc.id);
    }
    onNavigateToView('workspace');
  };

  // Filtered files
  const filteredFiles = uploadedFiles.filter(f => 
    f.original_filename.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 54px)', background: 'var(--bg-primary)', overflow: 'hidden' }}>
      
      {/* Notion-Style File grid list */}
      <div style={{ flex: 1, padding: '24px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        
        {/* Page title */}
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-primary)', margin: '0 0 4px 0' }}>Documents Library</h1>
          <p style={{ color: 'var(--text-muted)', margin: 0, fontSize: '0.85rem' }}>Upload files, inspect extraction pipelines, and launch AI chat workspaces.</p>
        </div>

        {/* Drag and Drop Zone */}
        <div 
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
          style={{
            border: dragActive ? '2px dashed var(--color-accent)' : '2px dashed var(--border-subtle)',
            borderRadius: '8px',
            background: dragActive ? 'rgba(139,92,246,0.05)' : 'var(--bg-panel)',
            padding: '30px',
            textAlign: 'center',
            cursor: 'pointer',
            position: 'relative',
            transition: 'all 0.2s'
          }}
        >
          <input 
            type="file" 
            id="file-upload-input" 
            multiple={false} 
            onChange={handleFileInput}
            style={{ display: 'none' }} 
          />
          <label htmlFor="file-upload-input" style={{ cursor: 'pointer', display: 'block' }}>
            <Upload size={32} style={{ color: 'var(--text-muted)', marginBottom: '10px' }} />
            <div style={{ fontWeight: 600, fontSize: '0.9rem', marginBottom: '4px' }}>
              {isUploading ? 'Uploading file...' : 'Drag & Drop document or click to browse'}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-disabled)' }}>
              Supports PDF, TXT, JSON, DOCX up to 50MB
            </div>
          </label>
        </div>

        {/* Filter Toolbar */}
        <div style={{ display: 'flex', gap: '12px' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <Search size={14} style={{ position: 'absolute', left: '12px', top: '12px', color: 'var(--text-muted)' }} />
            <input 
              type="text" 
              placeholder="Search documents by filename..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                background: 'var(--bg-panel)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '6px',
                padding: '10px 16px 10px 36px',
                color: 'var(--text-primary)',
                fontSize: '0.85rem'
              }}
            />
          </div>
        </div>

        {/* Table Viewport */}
        <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '8px', overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-subtle)', background: 'rgba(255,255,255,0.02)' }}>
                <th style={{ padding: '12px 16px', color: 'var(--text-muted)' }}>Name</th>
                <th style={{ padding: '12px 16px', color: 'var(--text-muted)' }}>Status</th>
                <th style={{ padding: '12px 16px', color: 'var(--text-muted)' }}>Page Count</th>
                <th style={{ padding: '12px 16px', color: 'var(--text-muted)' }}>File Size</th>
                <th style={{ padding: '12px 16px', color: 'var(--text-muted)' }}>Created</th>
              </tr>
            </thead>
            <tbody>
              {filteredFiles.map(file => {
                const isSelected = selectedFileDetail?.id === file.id;
                return (
                  <tr 
                    key={file.id}
                    onClick={() => setSelectedFileDetail(file)}
                    style={{
                      borderBottom: '1px solid var(--border-subtle)',
                      background: isSelected ? 'rgba(255,255,255,0.03)' : 'transparent',
                      cursor: 'pointer',
                      transition: 'background 0.2s'
                    }}
                  >
                    <td style={{ padding: '14px 16px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <FileText size={16} style={{ color: 'var(--text-muted)' }} />
                      {file.original_filename}
                    </td>
                    <td style={{ padding: '14px 16px' }}>
                      <Badge variant={file.status === 'completed' ? 'success' : file.status === 'failed' ? 'failure' : 'warning'}>
                        {file.status}
                      </Badge>
                    </td>
                    <td style={{ padding: '14px 16px' }}>{file.page_count || 12} pages</td>
                    <td style={{ padding: '14px 16px' }}>{file.size_bytes ? `${Math.round(file.size_bytes / 1024)} KB` : '4.2 MB'}</td>
                    <td style={{ padding: '14px 16px', color: 'var(--text-muted)' }}>{new Date(file.created_at).toLocaleDateString()}</td>
                  </tr>
                );
              })}
              {filteredFiles.length === 0 && (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-disabled)' }}>
                    No files found in library database.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

      </div>

      {/* Side Details Panel */}
      {selectedFileDetail && (
        <div style={{ width: '320px', borderLeft: '1px solid var(--border-subtle)', background: 'var(--bg-panel)', padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px', flexShrink: 0 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700 }}>Document Details</h3>
            <button onClick={() => setSelectedFileDetail(null)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>✕</button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', background: 'var(--bg-primary)', padding: '16px', borderRadius: '6px', border: '1px solid var(--border-subtle)' }}>
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-disabled)' }}>FILENAME</div>
              <div style={{ fontSize: '0.85rem', fontWeight: 600, wordBreak: 'break-all' }}>{selectedFileDetail.original_filename}</div>
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-disabled)' }}>DOCUMENT STATUS</div>
              <div style={{ display: 'flex', gap: '6px', alignItems: 'center', marginTop: '4px' }}>
                <Badge variant={selectedFileDetail.status === 'completed' ? 'success' : 'warning'}>{selectedFileDetail.status}</Badge>
              </div>
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-disabled)' }}>METADATA INDEX</div>
              <div style={{ fontSize: '0.85rem' }}>142 chunks | 86 entities</div>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: 'auto' }}>
            <Button 
              variant="primary" 
              onClick={() => handleChatDocument(selectedFileDetail)} 
              disabled={selectedFileDetail.status !== 'completed'}
              style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
            >
              <MessageSquare size={14} />
              Open In Workspace
            </Button>
            <Button 
              variant="secondary" 
              style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', color: 'var(--color-failure)' }}
            >
              <Trash2 size={14} />
              Delete Document
            </Button>
          </div>
        </div>
      )}

    </div>
  );
};

export default DocumentsLibrary;
