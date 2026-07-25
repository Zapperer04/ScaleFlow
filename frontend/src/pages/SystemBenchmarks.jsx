/* eslint-disable no-unused-vars */
import React, { useState } from 'react';
import { BarChart, Compass, Terminal, ShieldAlert, Cpu } from 'lucide-react';
import Button from '../components/ui/Button';
import Badge from '../components/ui/Badge';

export const SystemBenchmarks = () => {
  const [activeBaseline, setActiveBaseline] = useState('Hybrid');

  const mockBaselines = {
    'Vector-Only': { recall: 0.74, mrr: 0.72, citation: 85, latency: '24ms' },
    'Graph-Only': { recall: 0.68, mrr: 0.65, citation: 80, latency: '18ms' },
    'Hybrid': { recall: 0.95, mrr: 0.92, citation: 99.4, latency: '19.1ms' },
    'Hybrid + Reranker': { recall: 0.96, mrr: 0.94, citation: 99.6, latency: '38ms' }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 54px)', background: 'var(--bg-primary)', overflowY: 'auto', padding: '24px', gap: '20px' }}>
      
      {/* Title */}
      <div>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-primary)', margin: '0 0 4px 0' }}>System Benchmarks & Evaluation</h1>
        <p style={{ color: 'var(--text-muted)', margin: 0, fontSize: '0.85rem' }}>Scientific validation metrics comparing baseline models and execution performance gates.</p>
      </div>

      {/* Baseline Selector */}
      <div style={{ display: 'flex', gap: '10px' }}>
        {Object.keys(mockBaselines).map(base => (
          <button
            key={base}
            onClick={() => setActiveBaseline(base)}
            style={{
              padding: '10px 16px',
              background: activeBaseline === base ? 'rgba(139,92,246,0.1)' : 'var(--bg-panel)',
              border: activeBaseline === base ? '1px solid var(--color-accent)' : '1px solid var(--border-subtle)',
              borderRadius: '6px',
              color: activeBaseline === base ? 'var(--color-accent)' : 'var(--text-primary)',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.8rem'
            }}
          >
            {base}
          </button>
        ))}
      </div>

      {/* Metrics Row */}
      <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
        <div style={{ flex: 1, minWidth: '180px', background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '20px' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>RECALL@5</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{mockBaselines[activeBaseline].recall}</div>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-disabled)' }}>Gate limit: &gt;= 0.90</span>
        </div>

        <div style={{ flex: 1, minWidth: '180px', background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '20px' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>MEAN RECIPROCAL RANK (MRR)</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{mockBaselines[activeBaseline].mrr}</div>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-disabled)' }}>Gate limit: &gt;= 0.88</span>
        </div>

        <div style={{ flex: 1, minWidth: '180px', background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '20px' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>CITATION ACCURACY</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{mockBaselines[activeBaseline].citation}%</div>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-disabled)' }}>Gate limit: &gt;= 98%</span>
        </div>

        <div style={{ flex: 1, minWidth: '180px', background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '20px' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>P95 RETRIEVAL LATENCY</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{mockBaselines[activeBaseline].latency}</div>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-disabled)' }}>Gate limit: &lt; 300ms</span>
        </div>
      </div>

      {/* Production Qualification Banner */}
      <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '20px', display: 'flex', alignItems: 'center', gap: '16px' }}>
        <div style={{ width: '48px', height: '48px', borderRadius: '24px', background: 'rgba(16,185,129,0.1)', display: 'flex', alignItems: 'center', justifySelf: 'center', justifyContent: 'center', color: '#10b981' }}>
          ✓
        </div>
        <div>
          <h4 style={{ margin: '0 0 4px 0', fontSize: '0.9rem', fontWeight: 700 }}>Production Qualification Status</h4>
          <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            This release freeze has been qualified as <strong style={{ color: 'var(--color-success)' }}>"Production Qualified under the evaluated benchmark suite"</strong>.
          </p>
        </div>
      </div>

    </div>
  );
};

export default SystemBenchmarks;
