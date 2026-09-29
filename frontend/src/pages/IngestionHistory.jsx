import React, { useEffect, useState, useMemo } from 'react';
import { useDocument } from '../contexts/DocumentContext';
import { usePipeline } from '../contexts/PipelineContext';
import { useNotification } from '../contexts/NotificationContext';
import { fetchUploadedFiles, deleteDocument } from '../services/documents';
import { FileText, Trash2, ExternalLink, RefreshCw, Search } from 'lucide-react';
import ConfirmDialog from '../components/ui/ConfirmDialog';

const IngestionHistory = ({ onNavigateToView }) => {
  const { uploadedFiles, setUploadedFiles, setSelectedDocumentId } = useDocument();
  const { pipelines, setSelectedPipelineId } = usePipeline();
  const { addNotification } = useNotification();
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [loading, setLoading] = useState(false);
  const [deleteTargetDoc, setDeleteTargetDoc] = useState(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  const loadData = React.useCallback(async () => {
    setLoading(true);
    try {
      const files = await fetchUploadedFiles();
      setUploadedFiles(prev => {
        if (JSON.stringify(prev) === JSON.stringify(files)) return prev;
        return files || [];
      });
    } catch (err) {
      console.error('Failed to reload history:', err);
    } finally {
      setLoading(false);
    }
  }, [setUploadedFiles]);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 6000);
    return () => clearInterval(interval);
  }, [loadData]);

  const handleDeleteClick = (doc) => {
    setDeleteTargetDoc(doc);
  };

  const handleConfirmDelete = async () => {
    if (!deleteTargetDoc) return;
    const doc = deleteTargetDoc;
    setDeleteLoading(true);
    try {
      await deleteDocument(doc.id);
      addNotification(`Document "${doc.original_filename}" was permanently deleted.`, 'danger', 'system');
      setDeleteTargetDoc(null);
      await loadData();
    } catch (err) {
      addNotification(`Delete failed: ${err.message}`, 'error', 'system');
    } finally {
      setDeleteLoading(false);
    }
  };

  const handleOpen = (doc) => {
    setSelectedDocumentId(doc.id);
    const assoc = pipelines.find(p => p.file_id === doc.id || p.id === doc.pipeline_id);
    const targetPipelineId = assoc ? assoc.id : doc.pipeline_id;
    if (targetPipelineId) {
      setSelectedPipelineId(targetPipelineId);
    }
    const s = (doc.status || '').toLowerCase();
    if (s === 'failed' || s === 'blocked' || s === 'cancelled') {
      addNotification(`Document "${doc.original_filename}" failed processing. Opening Pipeline Monitor.`, 'warning', 'system');
      onNavigateToView('pipelines');
    } else {
      onNavigateToView('chat');
    }
  };

  const filteredDocs = useMemo(() => {
    return (uploadedFiles || []).filter(doc => {
      const matchesSearch = doc.original_filename?.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesStatus = statusFilter === 'ALL' || (doc.status || '').toUpperCase() === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [uploadedFiles, searchTerm, statusFilter]);

  return (
    <div style={{ padding: '32px', color: '#fff', display: 'flex', flexDirection: 'column', gap: '24px', height: '100%', overflowY: 'auto' }}>
      <div>
        <h1 style={{ margin: '0 0 8px 0', fontSize: '1.6rem', fontWeight: 800 }}>Ingestion History</h1>
        <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--text-muted)' }}>
          Monitor, open, delete, and inspect all document ingestion pipelines in one place.
        </p>
      </div>

      <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: '240px' }}>
          <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input
            type="text"
            placeholder="Search documents..."
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            style={{
              width: '100%',
              padding: '10px 12px 10px 36px',
              background: 'rgba(255,255,255,0.02)',
              border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: '8px',
              color: '#fff',
              fontSize: '0.85rem'
            }}
          />
        </div>

        <select
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
          style={{
            padding: '10px 16px',
            background: 'rgba(255,255,255,0.02)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '8px',
            color: '#fff',
            fontSize: '0.85rem',
            cursor: 'pointer'
          }}
        >
          <option value="ALL" style={{ background: '#0b1020' }}>All Statuses</option>
          <option value="COMPLETED" style={{ background: '#0b1020' }}>Completed</option>
          <option value="PROCESSING" style={{ background: '#0b1020' }}>Processing</option>
          <option value="FAILED" style={{ background: '#0b1020' }}>Failed</option>
        </select>

        <button
          onClick={loadData}
          disabled={loading}
          style={{
            padding: '10px 16px',
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '8px',
            color: '#fff',
            fontSize: '0.85rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <RefreshCw size={14} className={loading ? 'spin' : ''} />
          Refresh
        </button>
      </div>

      <div style={{ border: '1px solid rgba(255,255,255,0.06)', borderRadius: '12px', background: 'rgba(255,255,255,0.01)', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.02)' }}>
              <th style={{ padding: '14px 18px', fontWeight: 600, color: 'var(--text-secondary)' }}>Document</th>
              <th style={{ padding: '14px 18px', fontWeight: 600, color: 'var(--text-secondary)' }}>Upload Date</th>
              <th style={{ padding: '14px 18px', fontWeight: 600, color: 'var(--text-secondary)' }}>Status</th>
              <th style={{ padding: '14px 18px', fontWeight: 600, color: 'var(--text-secondary)' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredDocs.length > 0 ? (
              filteredDocs.map(doc => {
                const s = (doc.status || '').toLowerCase();
                const statusColor = (s === 'completed' || s === 'processed')
                  ? 'var(--color-success)'
                  : (s === 'failed' || s === 'blocked' || s === 'cancelled')
                  ? 'var(--color-failure)'
                  : 'var(--color-warning)';

                return (
                  <tr key={doc.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <td style={{ padding: '14px 18px', display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <FileText size={18} style={{ color: 'var(--color-accent)' }} />
                      <div>
                        <div style={{ fontWeight: 600 }}>{doc.original_filename}</div>
                        <div style={{ fontSize: '11px', color: 'var(--text-disabled)' }}>
                          {doc.size_bytes ? `${Math.round(doc.size_bytes / 1024)} KB` : '—'}
                        </div>
                      </div>
                    </td>
                    <td style={{ padding: '14px 18px', color: 'var(--text-secondary)' }}>
                      {doc.created_at ? new Date(doc.created_at).toLocaleString() : '—'}
                    </td>
                    <td style={{ padding: '14px 18px' }}>
                      <span style={{
                        fontSize: '10px',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        color: statusColor,
                        background: `${statusColor}15`,
                        border: `1px solid ${statusColor}30`,
                        borderRadius: '20px',
                        padding: '3px 8px'
                      }}>
                        {doc.status}
                      </span>
                    </td>
                    <td style={{ padding: '14px 18px' }}>
                      <div style={{ display: 'flex', gap: '10px' }}>
                        <button
                          onClick={() => handleOpen(doc)}
                          style={{
                            background: 'none',
                            border: '1px solid rgba(255,255,255,0.1)',
                            borderRadius: '6px',
                            color: '#fff',
                            padding: '6px 12px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                            fontSize: '11px',
                            fontWeight: 600
                          }}
                        >
                          <ExternalLink size={12} />
                          Open
                        </button>
                        <button
                          onClick={() => handleDeleteClick(doc)}
                          style={{
                            background: 'none',
                            border: '1px solid rgba(239,68,68,0.2)',
                            borderRadius: '6px',
                            color: '#ef4444',
                            padding: '6px 12px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                            fontSize: '11px',
                            fontWeight: 600
                          }}
                        >
                          <Trash2 size={12} />
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            ) : (
              <tr>
                <td colSpan="4" style={{ padding: '36px', textAlign: 'center', color: 'var(--text-disabled)' }}>
                  No ingestion history records found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <ConfirmDialog
        isOpen={!!deleteTargetDoc}
        title="Delete Document & Pipeline Data"
        message={`Are you sure you want to permanently delete "${deleteTargetDoc?.original_filename}" and all associated pipeline data? This action cannot be undone.`}
        confirmText="Delete Document"
        cancelText="Cancel"
        variant="danger"
        loading={deleteLoading}
        onConfirm={handleConfirmDelete}
        onCancel={() => setDeleteTargetDoc(null)}
      />

      <style>{`
        .spin {
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default IngestionHistory;
