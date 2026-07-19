import React from 'react';
import Card from '../../ui/Card';
import Badge from '../../ui/Badge';

/**
 * Renders an individual chunk matched during vector similarity retrieval.
 */
export const SearchResultItem = React.memo(({ citation, index }) => {
  const score = citation.score || citation.distance || 0.0;
  const chunkId = citation.chunk_id || citation.id || index;
  const content = citation.content || citation.text || citation.excerpt || '';

  return (
    <Card 
      className="search-result-citation-card"
      style={{ background: 'var(--bg-input)', borderColor: 'var(--border-divider)' }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-8)' }}>
        <span className="text-caption" style={{ fontWeight: 'var(--font-weight-bold)', color: 'var(--text-secondary)' }}>
          Citation #{index + 1} (Chunk ID: {chunkId})
        </span>
        <Badge variant={score > 0.8 ? 'success' : 'info'}>
          Score: {score.toFixed(3)}
        </Badge>
      </div>
      <p className="text-body" style={{ margin: 0, fontStyle: 'italic', color: 'var(--text-primary)', lineHeight: '1.4' }}>
        "{content.length > 300 ? `${content.slice(0, 300)}...` : content}"
      </p>
    </Card>
  );
});
export default SearchResultItem;
