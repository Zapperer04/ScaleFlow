import React from 'react';
import Card from '../../ui/Card';
import Badge from '../../ui/Badge';
import ProgressBar from '../../ui/ProgressBar';
import EmptyState from '../../ui/EmptyState';
import useRecentDocuments from './useRecentDocuments';

/**
 * List view of recently uploaded document ingestion runs.
 */
export const RecentDocuments = () => {
  const { documents = [], selectedDocId, handleSelectDocument } = useRecentDocuments();

  const getStatusVariant = (status) => {
    switch (status?.toLowerCase()) {
      case 'completed': return 'success';
      case 'failed': return 'danger';
      case 'running':
      case 'processing': return 'info';
      default: return 'warning';
    }
  };

  return (
    <Card 
      className="recent-documents-panel"
      header={<span className="text-h4" style={{ color: 'var(--text-primary)' }}>Ingestion Registry</span>}
    >
      {documents.length === 0 ? (
        <EmptyState 
          title="No Ingested Documents" 
          description="Upload a configuration file in the Ingestion panel above to start processing." 
        />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-12)', maxHeight: '350px', overflowY: 'auto' }}>
          {documents.map((doc) => {
            const isSelected = doc.id === selectedDocId;
            return (
              <div
                key={doc.id}
                onClick={() => handleSelectDocument(doc.id)}
                style={{
                  padding: 'var(--spacing-12)',
                  borderRadius: 'var(--radius-6)',
                  border: isSelected ? '2px solid var(--color-accent)' : '1px solid var(--border-subtle)',
                  background: isSelected ? 'var(--bg-hover)' : 'var(--bg-panel)',
                  cursor: 'pointer',
                  transition: 'var(--transition-fast-ease)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 'var(--spacing-8)'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span className="text-body" style={{ fontWeight: 'var(--font-weight-bold)', color: isSelected ? 'var(--color-accent)' : 'var(--text-primary)' }}>
                    {doc.filename}
                  </span>
                  <Badge variant={getStatusVariant(doc.status)}>
                    {doc.status}
                  </Badge>
                </div>
                
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-12)' }}>
                  <div style={{ flex: 1 }}>
                    <ProgressBar progress={doc.progress} variant={getStatusVariant(doc.status)} />
                  </div>
                  <span className="text-caption" style={{ color: 'var(--text-secondary)', minWidth: '32px', textAlign: 'right' }}>
                    {doc.progress}%
                  </span>
                </div>

                <div className="text-caption" style={{ color: 'var(--text-disabled)', display: 'flex', justifyContent: 'space-between' }}>
                  <span>Ingestion ID: #{doc.id}</span>
                  <span>{new Date(doc.timestamp).toLocaleTimeString()}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
};
export default RecentDocuments;
