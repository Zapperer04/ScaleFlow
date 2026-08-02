import React, { useState, useRef } from 'react';
import { usePipeline } from '../../../contexts/PipelineContext';
import { Send, Sparkles, HelpCircle, AlertOctagon, RefreshCw } from 'lucide-react';
import Button from '../../ui/Button';

export const QueryWorkbench = () => {
  const { selectedPipelineId, queryResult, submitQueryStream, setQueryResult } = usePipeline();
  const [queryText, setQueryText] = useState('What projects has this candidate completed?');
  const [loading, setLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamedAnswer, setStreamedAnswer] = useState('');
  const [streamedCitations, setStreamedCitations] = useState([]);
  
  const abortControllerRef = useRef(null);

  const handleQuerySubmit = async (e, forceText = null) => {
    if (e) e.preventDefault();
    const finalQuery = forceText || queryText;
    if (!finalQuery.trim() || !selectedPipelineId) return;

    setLoading(true);
    setIsStreaming(true);
    setStreamedAnswer('');
    setStreamedCitations([]);
    setQueryResult(null);

    // Setup Abort Controller
    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      await submitQueryStream(
        finalQuery,
        selectedPipelineId,
        (token) => {
          if (controller.signal.aborted) return;
          setStreamedAnswer(prev => prev + token);
        },
        (citation) => {
          if (controller.signal.aborted) return;
          setStreamedCitations(prev => [...prev, citation]);
        },
        (complete) => {
          setIsStreaming(false);
          setLoading(false);
          // Set full queryResult to preserve compatibility with other inspector panels
          setQueryResult({
            answer: streamedAnswer,
            citations: streamedCitations,
            latency: { total: 0.8 },
            intent: "factual",
            routing: { confidence: 0.95 }
          });
        }
      );
    } catch (err) {
      console.error("Streaming error", err);
      setIsStreaming(false);
      setLoading(false);
    }
  };

  const handleAbort = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsStreaming(false);
      setLoading(false);
      setStreamedAnswer(prev => prev + " [Generation Aborted by User]");
    }
  };

  const handleRetry = () => {
    handleQuerySubmit(null);
  };

  const displayAnswer = isStreaming ? streamedAnswer : (queryResult?.answer || streamedAnswer);
  const displayCitations = isStreaming ? streamedCitations : (queryResult?.citations || streamedCitations);

  return (
    <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '20px', display: 'flex', flexDirection: 'column', height: '100%', minHeight: '400px' }}>
      <h3 style={{ margin: '0 0 16px 0', fontSize: '0.9rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <Sparkles size={16} style={{ color: 'var(--color-accent)' }} />
        Multimodal Graph RAG Query Workbench
      </h3>

      <form onSubmit={(e) => handleQuerySubmit(e)} style={{ display: 'flex', gap: '10px', marginBottom: '16px' }}>
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
        
        {isStreaming ? (
          <Button variant="danger" type="button" onClick={handleAbort} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <AlertOctagon size={14} />
            Abort
          </Button>
        ) : (
          <Button variant="primary" type="submit" disabled={loading || !selectedPipelineId} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Send size={14} />
            Ask
          </Button>
        )}
      </form>

      {!selectedPipelineId && (
        <div style={{ color: 'var(--color-warning)', fontSize: '0.8rem', marginBottom: '12px', background: 'rgba(245, 158, 11, 0.1)', padding: '10px', borderRadius: '4px' }}>
          Warning: Select a workspace pipeline first to query.
        </div>
      )}

      {loading && isStreaming && !displayAnswer && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-muted)', fontSize: '0.85rem', padding: '10px' }}>
          <span className="typing-indicator" style={{ display: 'inline-flex', gap: '3px' }}>
            <span style={{ width: '6px', height: '6px', background: 'var(--color-accent)', borderRadius: '50%', animation: 'bounce 1.4s infinite ease-in-out both' }} />
            <span style={{ width: '6px', height: '6px', background: 'var(--color-accent)', borderRadius: '50%', animation: 'bounce 1.4s infinite ease-in-out both 0.2s' }} />
            <span style={{ width: '6px', height: '6px', background: 'var(--color-accent)', borderRadius: '50%', animation: 'bounce 1.4s infinite ease-in-out both 0.4s' }} />
          </span>
          Initializing query stream and parsing layout structures...
        </div>
      )}

      {displayAnswer || displayCitations.length > 0 ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', overflowY: 'auto', flex: 1 }}>
          {/* Answer Box */}
          <div style={{ background: 'var(--bg-primary)', padding: '16px', borderRadius: '6px', borderLeft: '4px solid var(--color-accent)', minHeight: '100px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 'bold' }}>GROUNDED STREAM ANSWER</div>
              {!isStreaming && (
                <button 
                  onClick={handleRetry} 
                  style={{ background: 'none', border: 'none', color: 'var(--color-accent)', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer' }}
                >
                  <RefreshCw size={10} />
                  Retry
                </button>
              )}
            </div>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
              {displayAnswer}
            </div>
          </div>

          {/* Citations Box */}
          {displayCitations.length > 0 && (
            <div style={{ background: 'var(--bg-primary)', padding: '12px', borderRadius: '6px', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--text-primary)', marginBottom: '8px' }}>Traceable Citations</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {displayCitations.map((cit, idx) => (
                  <div key={idx} style={{ background: 'rgba(59, 130, 246, 0.1)', border: '1px solid rgba(59, 130, 246, 0.2)', padding: '6px 10px', borderRadius: '4px', fontSize: '0.75rem', color: 'var(--color-accent)' }}>
                    {cit.source || cit.file || "Document Source"} (Chunk: {cit.chunk_id || idx + 1})
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        !loading && (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', gap: '8px' }}>
            <HelpCircle size={32} style={{ opacity: 0.5 }} />
            <span style={{ fontSize: '0.85rem' }}>Submit a query above to generate a grounded answer with traceable citations.</span>
          </div>
        )
      )}
    </div>
  );
};
export default QueryWorkbench;
