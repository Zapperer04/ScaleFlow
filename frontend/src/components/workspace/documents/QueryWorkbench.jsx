import React, { useState } from 'react';
import { usePipeline } from '../../../contexts/PipelineContext';
import { Send, Clock, Sparkles, HelpCircle } from 'lucide-react';
import Button from '../../ui/Button';

export const QueryWorkbench = () => {
  const { selectedPipelineId, queryResult, submitQuery } = usePipeline();
  const [queryText, setQueryText] = useState('What projects has this candidate completed?');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!queryText.trim() || !selectedPipelineId) return;
    setLoading(true);
    await submitQuery(queryText, selectedPipelineId);
    setLoading(false);
  };

  const latency = queryResult?.latency || {};
  const answer = queryResult?.answer;

  return (
    <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '20px', display: 'flex', flexDirection: 'column', height: '100%', minHeight: '400px' }}>
      <h3 style={{ margin: '0 0 16px 0', fontSize: '0.9rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <Sparkles size={16} style={{ color: 'var(--color-accent)' }} />
        Multimodal Graph RAG Query Workbench
      </h3>

      <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '10px', marginBottom: '16px' }}>
        <input
          type="text"
          value={queryText}
          onChange={(e) => setQueryText(e.target.value)}
          placeholder="Ask a question about the document..."
          disabled={loading || !selectedPipelineId}
          style={{
            flex: 1,
            background: 'var(--bg-primary)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '6px',
            padding: '10px 14px',
            color: 'var(--text-primary)',
            fontSize: '0.85rem'
          }}
        />
        <Button variant="primary" type="submit" disabled={loading || !selectedPipelineId} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {loading ? (
            <span style={{ fontSize: '0.8rem' }}>Querying...</span>
          ) : (
            <>
              <Send size={14} />
              Ask
            </>
          )}
        </Button>
      </form>

      {!selectedPipelineId && (
        <div style={{ color: 'var(--color-warning)', fontSize: '0.8rem', marginBottom: '12px', background: 'rgba(245, 158, 11, 0.1)', padding: '10px', borderRadius: '4px' }}>
          Warning: Select a workspace pipeline first to query.
        </div>
      )}

      {queryResult ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', overflowY: 'auto', flex: 1 }}>
          {/* Latency and Details */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-primary)', padding: '10px 14px', borderRadius: '6px', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-muted)' }}>
              <Clock size={14} />
              Latency: {(latency.total || 0).toFixed(2)}s
            </span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Routing: {queryResult.intent} ({(queryResult.routing?.confidence * 100).toFixed(0)}%)
            </span>
          </div>

          {/* Reasoning Explainability */}
          {queryResult.routing?.reasoning && (
            <div style={{ background: 'var(--bg-primary)', padding: '12px', borderRadius: '6px', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--text-primary)', marginBottom: '6px' }}>Intent Routing Reasoning</div>
              <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                {queryResult.routing.reasoning.map((r, rIdx) => (
                  <li key={rIdx}>{r}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Answer Box */}
          <div style={{ background: 'var(--bg-primary)', padding: '16px', borderRadius: '6px', borderLeft: '4px solid var(--color-accent)', minHeight: '100px' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '8px', fontWeight: 'bold' }}>GROUNDED ANSWER</div>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)', lineHeight: 1.6 }}>
              {answer}
            </div>
          </div>
        </div>
      ) : (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', gap: '8px' }}>
          <HelpCircle size={32} style={{ opacity: 0.5 }} />
          <span style={{ fontSize: '0.85rem' }}>Submit a query above to generate a grounded answer with traceable citations.</span>
        </div>
      )}
    </div>
  );
};
export default QueryWorkbench;
