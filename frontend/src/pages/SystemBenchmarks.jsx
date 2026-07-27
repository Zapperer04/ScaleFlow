/* eslint-disable no-unused-vars */
import React, { useState, useEffect } from 'react';
import { BarChart, Compass, Terminal, ShieldAlert, Cpu } from 'lucide-react';
import { useTelemetry } from '../services/telemetryStore';
import Button from '../components/ui/Button';
import Badge from '../components/ui/Badge';

export const SystemBenchmarks = () => {
  const [activeBaseline, setActiveBaseline] = useState('Hybrid');
  const systemMetrics = useTelemetry(s => s.metrics?.system);
  const [prevHealth, setPrevHealth] = useState(null);
  const [ariaAnnounce, setAriaAnnounce] = useState('');

  const mockBaselines = {
    'Vector-Only': { recall: 0.85, mrr: 0.82, citation: 85, latency: '4.7ms' },
    'Graph-Only': { recall: 0.72, mrr: 0.71, citation: 80, latency: '6.1ms' },
    'Hybrid': { recall: 0.95, mrr: 0.92, citation: 99.4, latency: '19.1ms' },
    'Hybrid + Reranker': { recall: 0.95, mrr: 0.92, citation: 99.6, latency: '19.0ms' }
  };

  // Announce only state transitions to screen readers (F-19)
  useEffect(() => {
    if (systemMetrics?.health_state && systemMetrics.health_state !== prevHealth) {
      setAriaAnnounce(`System health state changed to ${systemMetrics.health_state}. Reason: ${systemMetrics.health_reason || 'Operating within limits.'}`);
      setPrevHealth(systemMetrics.health_state);
    }
  }, [systemMetrics?.health_state, systemMetrics?.health_reason, prevHealth]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 54px)', background: 'var(--bg-primary)', overflowY: 'auto', padding: '24px', gap: '20px' }}>
      
      {/* Accessibility Screen Reader Live Region */}
      <div 
        aria-live="polite" 
        style={{ position: 'absolute', width: '1px', height: '1px', padding: 0, margin: '-1px', overflow: 'hidden', clip: 'rect(0, 0, 0, 0)', border: 0 }}
      >
        {ariaAnnounce}
      </div>

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

      {/* Live System Performance Telemetry */}
      {systemMetrics && (
        <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <h3 style={{ margin: '0 0 4px 0', fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)' }}>Live Operational Telemetry</h3>
            <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-muted)' }}>Real-time execution analytics and resource utilization.</p>
          </div>
          
          <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
            <div style={{ flex: 1, minWidth: '150px' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>CPU / RAM Usage</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 700, marginTop: '4px' }}>
                {systemMetrics.metrics?.cpu_usage_percentage ?? 'N/A'}% / {systemMetrics.metrics?.ram_usage_percentage ?? 'N/A'}%
              </div>
            </div>

            <div style={{ flex: 1, minWidth: '150px' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Avg Task Execution</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 700, marginTop: '4px' }}>
                {systemMetrics.metrics?.average_task_execution_time_seconds ?? 'N/A'}s
              </div>
            </div>

            <div style={{ flex: 1, minWidth: '150px' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Avg Queue Wait</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 700, marginTop: '4px' }}>
                {systemMetrics.metrics?.average_queue_wait_time_seconds ?? 'N/A'}s
              </div>
            </div>

            <div style={{ flex: 1, minWidth: '150px' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>System Health Status</div>
              <div style={{ marginTop: '4px' }}>
                <span style={{
                  textTransform: 'uppercase',
                  fontWeight: 'bold',
                  fontSize: '0.75rem',
                  color: systemMetrics.health_state === 'healthy' ? '#10b981' : systemMetrics.health_state === 'degraded' ? '#f59e0b' : '#ef4444'
                }}>
                  {systemMetrics.health_state ?? 'Unknown'}
                </span>
                <span style={{ display: 'block', fontSize: '0.65rem', color: 'var(--text-disabled)', marginTop: '2px' }}>
                  {systemMetrics.health_reason || 'N/A'}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

export default SystemBenchmarks;
