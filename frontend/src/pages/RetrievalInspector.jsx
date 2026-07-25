/* eslint-disable no-unused-vars */
import React, { useState } from 'react';
import { Search, Compass, Share2, Server, HelpCircle, FileText, CheckCircle2 } from 'lucide-react';
import Button from '../components/ui/Button';
import Badge from '../components/ui/Badge';

export const RetrievalInspector = () => {
  const [query, setQuery] = useState('What projects has this candidate completed?');
  const [explainMode, setExplainMode] = useState(true);

  const mockExperts = [
    { name: 'Vector Expert (Dense Cosine)', score: 0.942, weight: '40% (RRF)', matches: 3 },
    { name: 'Graph Expert (Section Hop)', score: 0.811, weight: '30% (RRF)', matches: 2 },
    { name: 'Entity Expert (Attribute Match)', score: 0.312, weight: '10% (RRF)', matches: 1 },
    { name: 'Table Expert (Cell Coordinates)', score: 0.420, weight: '20% (RRF)', matches: 1 }
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 54px)', background: 'var(--bg-primary)', overflowY: 'auto', padding: '24px', gap: '20px' }}>
      
      {/* Title */}
      <div>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-primary)', margin: '0 0 4px 0' }}>Retrieval Inspector Console</h1>
        <p style={{ color: 'var(--text-muted)', margin: 0, fontSize: '0.85rem' }}>Deep-dive analysis of query routing weights, expert agreements, and rerank distributions.</p>
      </div>

      {/* Query Bar */}
      <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '16px', display: 'flex', gap: '12px', alignItems: 'center' }}>
        <input 
          type="text" 
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Input search query..."
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
        <Button variant="primary" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Search size={14} />
          Analyze
        </Button>
      </div>

      {/* Grid panels */}
      <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
        
        {/* Left Side: Score Heatmap & Expert Agreement */}
        <div style={{ flex: 1, minWidth: '320px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {/* Expert Breakdown Panel */}
          <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '20px' }}>
            <h3 style={{ margin: '0 0 16px 0', fontSize: '0.9rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-primary)' }}>Expert Score Distributions</h3>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {mockExperts.map((exp, idx) => (
                <div key={idx}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '4px' }}>
                    <span style={{ fontWeight: 600 }}>{exp.name}</span>
                    <span style={{ color: 'var(--color-accent)' }}>Score: {exp.score} ({exp.weight})</span>
                  </div>
                  <div style={{ width: '100%', height: '6px', background: '#1e293b', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{ width: `${exp.score * 100}%`, height: '100%', background: 'linear-gradient(90deg, #8b5cf6 0%, #a78bfa 100%)' }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Reranker & Agreement */}
          <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '20px', display: 'flex', gap: '16px' }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>RERANKER CONFIDENCE</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--color-success)' }}>0.895</div>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-disabled)' }}>MS-MARCO Cross-Encoder</span>
            </div>
            <div style={{ flex: 1, borderLeft: '1px solid var(--border-subtle)', paddingLeft: '16px' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>AGREEMENT RATING</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--color-success)' }}>3 / 4 Experts</div>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-disabled)' }}>Identify identical top-3 context chunks</span>
            </div>
          </div>

        </div>

        {/* Right Side: SQLite Graph hops */}
        <div style={{ flex: 1, minWidth: '320px', background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '20px' }}>
          <h3 style={{ margin: '0 0 16px 0', fontSize: '0.9rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Compass size={16} />
            Graph Traversal Path
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ background: 'var(--bg-primary)', padding: '12px', borderRadius: '6px', borderLeft: '3px solid var(--color-accent)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', fontWeight: 'bold', marginBottom: '4px' }}>
                <span>[Origin Point] chunk_p1_n4</span>
                <Badge variant="success">Cosine: 0.942</Badge>
              </div>
              <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-muted)' }}>"Kaustav Kumar completed the ScaleFlow platform in 2026."</p>
            </div>
            
            <div style={{ textAlign: 'center', color: 'var(--text-disabled)', fontSize: '0.7rem' }}>↓ (Graph Hop: Child Reference)</div>

            <div style={{ background: 'var(--bg-primary)', padding: '12px', borderRadius: '6px', borderLeft: '3px solid var(--color-accent)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', fontWeight: 'bold', marginBottom: '4px' }}>
                <span>[Target Hop] chunk_p1_n5</span>
                <Badge variant="success">Hop Weight: 0.850</Badge>
              </div>
              <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-muted)' }}>"ScaleFlow was production qualified under evaluated datasets."</p>
            </div>
          </div>
        </div>

      </div>

    </div>
  );
};

export default RetrievalInspector;
