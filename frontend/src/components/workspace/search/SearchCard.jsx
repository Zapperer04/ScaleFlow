import React from 'react';
import Card from '../../ui/Card';
import Button from '../../ui/Button';
import SearchInput from '../../ui/SearchInput';
import Spinner from '../../ui/Spinner';
import Alert from '../../ui/Alert';
import SearchResults from './SearchResults';
import useSearch from './useSearch';

/**
 * Container component managing semantic search queries.
 */
export const SearchCard = () => {
  const {
    query,
    setQuery,
    loading,
    error,
    answer,
    results,
    executeSearch
  } = useSearch();

  return (
    <Card 
      className="search-card-panel"
      header={<span className="text-h4" style={{ color: 'var(--text-primary)' }}>2. Query Ingested Index</span>}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-16)' }}>
        
        {/* Search Input Bar */}
        <form onSubmit={executeSearch} style={{ display: 'flex', gap: 'var(--spacing-12)' }}>
          <div style={{ flex: 1 }}>
            <SearchInput
              placeholder="Ask a question about this configuration or trace..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={loading}
            />
          </div>
          <Button 
            variant="primary"
            type="submit"
            disabled={loading || !query.trim()}
            iconLeft={loading ? <Spinner size="sm" /> : undefined}
          >
            {loading ? 'Retrieving' : 'Ask'}
          </Button>
        </form>

        {/* Loading / Error States */}
        {loading && !answer && (
          <div style={{ padding: 'var(--spacing-24)', textAlign: 'center' }}>
            <Spinner size="md" />
            <div className="text-caption" style={{ color: 'var(--text-disabled)', marginTop: 'var(--spacing-8)' }}>
              Executing cosine similarity matching and LLM generation...
            </div>
          </div>
        )}

        {error && (
          <Alert variant="danger" title="Search Error">
            {error}
          </Alert>
        )}

        {/* Results Panel */}
        <SearchResults answer={answer} results={results} />
      </div>
    </Card>
  );
};
export default SearchCard;
