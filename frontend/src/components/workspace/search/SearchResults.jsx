import React from 'react';
import Badge from '../../ui/Badge';
import SearchResultItem from './SearchResultItem';

/**
 * Presentational list of search result citations and answers.
 */
export const SearchResults = ({ answer, results = [] }) => {
  if (!answer) return null;

  const confidenceVariant = 
    answer.confidence === 'high' ? 'success' : 
    answer.confidence === 'medium' ? 'warning' : 'danger';

  return (
    <div className="search-results-wrapper" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-16)', marginTop: 'var(--spacing-16)' }}>
      
      {/* 1. Answer Synthesis Box */}
      <div 
        className="synthesis-box" 
        style={{
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-6)',
          padding: 'var(--spacing-16)',
          background: 'var(--bg-hover)'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-12)' }}>
          <span className="text-body" style={{ fontWeight: 'var(--font-weight-bold)', color: 'var(--color-accent)' }}>
            Synthesized Ingestion Model Answer
          </span>
          <Badge variant={confidenceVariant}>
            Confidence: {answer.confidence}
          </Badge>
        </div>
        <p className="text-body" style={{ margin: 0, color: 'var(--text-primary)', lineHeight: '1.6' }}>
          {answer.answer}
        </p>
        <div style={{ display: 'flex', gap: 'var(--spacing-16)', borderTop: '1px solid var(--border-divider)', marginTop: 'var(--spacing-12)', paddingTop: 'var(--spacing-8)', color: 'var(--text-disabled)' }} className="text-caption">
          <span>Query Pipeline: #{answer.pipeline_id}</span>
          <span>Elapsed Time: {answer.elapsed_seconds.toFixed(2)}s</span>
        </div>
      </div>

      {/* 2. Citations List */}
      {results.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-12)' }}>
          <span className="text-caption" style={{ fontWeight: 'var(--font-weight-bold)', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Retrieved Context Chunks ({results.length})
          </span>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-8)' }}>
            {results.map((citation, index) => (
              <SearchResultItem 
                key={citation.chunk_id || citation.id || index}
                citation={citation}
                index={index}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
export default SearchResults;
