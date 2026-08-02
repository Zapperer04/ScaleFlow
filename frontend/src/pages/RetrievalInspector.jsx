import React from 'react';
import { usePipeline } from '../contexts/PipelineContext';
import { Layers, Activity } from 'lucide-react';
import Badge from '../components/ui/Badge';

export const RetrievalInspector = () => {
  const { queryResult } = usePipeline();

  const candidates = queryResult?.retrieval?.candidates || [];
  const reranked = queryResult?.reranking?.reranked_chunks || [];
  const routing = queryResult?.routing || {};

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 54px)', background: 'var(--bg-primary)', overflowY: 'auto', padding: '24px', gap: '20px' }}>
      
      {/* Title */}
      <div>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-primary)', margin: '0 0 4px 0' }}>Retrieval Inspector Console</h1>
        <p style={{ color: 'var(--text-muted)', margin: 0, fontSize: '0.85rem' }}>Deep-dive analysis of query routing weights, expert agreements, and rerank distributions.</p>
      </div>

      {/* Overview Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
        <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '16px' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>ROUTED INTENT</div>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--color-accent)', textTransform: 'capitalize' }}>
            {routing.intent || 'N/A'}
          </div>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-disabled)' }}>Query Router Intent Decision</span>
        </div>
        <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '16px' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>ROUTING CONFIDENCE</div>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--color-success)' }}>
            {routing.confidence ? `${(routing.confidence * 100).toFixed(1)}%` : 'N/A'}
          </div>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-disabled)' }}>Heuristic / Model Probability</span>
        </div>
        <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '16px' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>CANDIDATES POOL</div>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            {candidates.length} Chunks
          </div>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-disabled)' }}>Semantic + BM25 + Graph Hits</span>
        </div>
      </div>

      {/* Grid panels */}
      <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
        
        {/* Left: Candidates list with source provenance */}
        <div style={{ flex: 2, minWidth: '400px', background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '20px' }}>
          <h3 style={{ margin: '0 0 16px 0', fontSize: '0.9rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Layers size={16} />
            Candidates Pool & Retrieval Sources
          </h3>

          {candidates.length === 0 ? (
            <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textAlign: 'center', padding: '40px 0' }}>
              No retrieval candidates found. Submit a query in the Query Workbench to populate.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {candidates.map((cand, idx) => (
                <div key={idx} style={{ background: 'var(--bg-primary)', padding: '12px', borderRadius: '6px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <span style={{ fontWeight: 600, fontSize: '0.8rem', color: 'var(--text-primary)' }}>{cand.chunk_id}</span>
                    <div style={{ display: 'flex', gap: '6px' }}>
                      {cand.sources.map((src, sIdx) => (
                        <Badge key={sIdx} variant={src === 'semantic' ? 'primary' : src === 'graph' ? 'accent' : 'success'}>
                          {src}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '16px', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                    <span>Semantic: {cand.semantic_score?.toFixed(4) || '0.0000'}</span>
                    <span>BM25: {cand.bm25_score?.toFixed(2) || '0.0'}</span>
                    <span>Graph: {cand.graph_score?.toFixed(1) || '0.0'}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right: Reranked candidates list */}
        <div style={{ flex: 1.5, minWidth: '300px', background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '20px' }}>
          <h3 style={{ margin: '0 0 16px 0', fontSize: '0.9rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Activity size={16} />
            Deterministic Reranked Order
          </h3>

          {reranked.length === 0 ? (
            <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textAlign: 'center', padding: '40px 0' }}>
              No reranked order available yet.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {reranked.map((item, idx) => (
                <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '12px', background: 'var(--bg-primary)', padding: '10px', borderRadius: '6px', borderLeft: `3px solid ${idx === 0 ? 'var(--color-success)' : 'var(--color-accent)'}` }}>
                  <div style={{ width: '20px', height: '20px', borderRadius: '50%', background: 'var(--bg-panel)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--text-muted)' }}>
                    {idx + 1}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)' }}>{item.chunk_id}</span>
                      <span style={{ fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--color-success)' }}>
                        {item.score?.toFixed(4)}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                      Sources: {item.sources?.join(', ')}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

      </div>
    </div>
  );
};
export default RetrievalInspector;
