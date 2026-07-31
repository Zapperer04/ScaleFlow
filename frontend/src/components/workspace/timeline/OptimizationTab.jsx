import React, { useState, useMemo, useEffect } from 'react';

export const OptimizationTab = ({ optimizationModel, loading, error }) => {
  const optData = optimizationModel?.optimization || {};
  const { bottlenecks, recommendations, what_if, heatmaps, summary } = optData;
  const baseline = useMemo(() => what_if?.baseline || {}, [what_if]);
  const coefficients = useMemo(() => what_if?.coefficients || {}, [what_if]);

  // Sliders state
  const [workers, setWorkers] = useState(1);
  const [concurrency, setConcurrency] = useState(1.0);
  const [retriesScale, setRetriesScale] = useState(1.0);
  const [queueWaitScale, setQueueWaitScale] = useState(1.0);

  // Sync state with loaded baseline
  useEffect(() => {
    if (baseline.worker_count) {
      setWorkers(baseline.worker_count);
    }
  }, [baseline.worker_count]);

  // Recompute locally
  const simulation = useMemo(() => {
    if (!baseline || Object.keys(baseline).length === 0) return null;

    const W_base = baseline.worker_count || 1;
    const f_W = workers / W_base;
    const f_C = concurrency;
    const f_R = retriesScale;
    const f_Q = queueWaitScale;

    const cp_exec = baseline.critical_path_execution_ms || 0.0;
    const cp_retry = baseline.critical_path_retry_ms || 0.0;
    const cp_queue = baseline.critical_path_queue_wait_ms || 0.0;

    // Simulation Formula:
    // CP_new = CP_exec - CP_retry + (f_R * CP_retry) + (f_Q * queue_wait_factor * (1 / (f_W * f_C)) * CP_queue)
    const queue_wait_factor = coefficients.worker_scaling_factor || 1.0;
    const cp_queue_sim = f_Q * queue_wait_factor * (1.0 / (f_W * f_C)) * cp_queue;
    const cp_retry_sim = f_R * cp_retry;
    
    const sim_critical_path_duration_ms = (cp_exec - cp_retry) + cp_retry_sim + cp_queue_sim;

    const pipeline_base = baseline.pipeline_duration_ms || 10.0;
    const cp_base = baseline.critical_path_duration_ms || 10.0;

    const delta_cp = cp_base - sim_critical_path_duration_ms;
    const sim_pipeline_duration_ms = Math.max(sim_critical_path_duration_ms, pipeline_base - delta_cp, 10.0);

    const sim_parallel_efficiency = sim_critical_path_duration_ms / sim_pipeline_duration_ms;
    const time_saved_ms = Math.max(0.0, pipeline_base - sim_pipeline_duration_ms);
    const percentage_improvement = (time_saved_ms / pipeline_base) * 100.0;

    return {
      pipeline_duration_ms: sim_pipeline_duration_ms,
      critical_path_duration_ms: sim_critical_path_duration_ms,
      parallel_efficiency: sim_parallel_efficiency,
      time_saved_ms,
      percentage_improvement
    };
  }, [workers, concurrency, retriesScale, queueWaitScale, baseline, coefficients]);

  if (loading) {
    return (
      <div style={{ padding: '20px', color: 'var(--text-muted)', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <div className="spinner" style={{ width: '16px', height: '16px', border: '2px solid var(--text-muted)', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
        Running diagnostic optimization analysis...
        <style>{`
          @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        `}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '20px', color: 'var(--color-danger)', fontSize: '0.85rem' }}>
        <strong>Error:</strong> {error}
      </div>
    );
  }

  if (!optimizationModel || !optimizationModel.optimization) {
    return (
      <div style={{ padding: '20px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
        No optimization data available for this pipeline execution.
      </div>
    );
  }

  const getSeverityBadgeColor = (severity) => {
    switch (severity) {
      case 'critical': return 'rgba(239, 68, 68, 0.2)';
      case 'high': return 'rgba(249, 115, 22, 0.2)';
      case 'medium': return 'rgba(234, 179, 8, 0.2)';
      default: return 'rgba(59, 130, 246, 0.2)';
    }
  };

  const getSeverityTextColor = (severity) => {
    switch (severity) {
      case 'critical': return '#ef4444';
      case 'high': return '#f97316';
      case 'medium': return '#eab308';
      default: return '#3b82f6';
    }
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1.3fr 1.5fr', gap: '16px', height: '100%', overflow: 'hidden' }}>
      
      {/* LEFT COLUMN: BOTTLENECKS & HEATMAPS */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', overflowY: 'auto', paddingRight: '4px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
          <h4 style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-primary)', fontWeight: 600 }}>Active Bottlenecks</h4>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', background: 'var(--bg-panel-header)', padding: '2px 6px', borderRadius: '4px' }}>
            Score: {summary?.overall_score || 100}/100
          </span>
        </div>

        {bottlenecks && bottlenecks.length > 0 ? (
          bottlenecks.map((b) => (
            <div 
              key={b.id} 
              style={{ 
                background: 'var(--bg-input)', 
                borderLeft: `3px solid ${getSeverityTextColor(b.severity)}`, 
                borderRadius: '4px', 
                padding: '10px',
                boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-primary)' }}>{b.title}</span>
                <span style={{ 
                  fontSize: '0.65rem', 
                  textTransform: 'uppercase', 
                  fontWeight: 700, 
                  padding: '2px 6px', 
                  borderRadius: '3px',
                  background: getSeverityBadgeColor(b.severity),
                  color: getSeverityTextColor(b.severity)
                }}>
                  {b.severity}
                </span>
              </div>
              <p style={{ margin: '6px 0 0 0', fontSize: '0.7rem', color: 'var(--text-muted)', lineHeight: '1.3' }}>{b.description}</p>
              {b.affected_duration_ms > 0 && (
                <div style={{ marginTop: '8px', fontSize: '0.65rem', color: 'var(--text-muted)', display: 'flex', justifyContent: 'space-between' }}>
                  <span>Impact Magnitude:</span>
                  <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{(b.affected_duration_ms / 1000.0).toFixed(2)}s</span>
                </div>
              )}
            </div>
          ))
        ) : (
          <div style={{ background: 'var(--bg-input)', padding: '12px', borderRadius: '4px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            No bottlenecks detected.
          </div>
        )}

        {/* Heatmaps Section */}
        <div style={{ marginTop: '12px', background: 'var(--bg-input)', borderRadius: '6px', padding: '12px' }}>
          <h5 style={{ margin: '0 0 10px 0', fontSize: '0.8rem', color: 'var(--text-primary)', fontWeight: 600 }}>Congestion Heatmaps</h5>
          
          {/* Worker Saturation */}
          <div style={{ marginBottom: '8px' }}>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block', marginBottom: '3px' }}>Worker Saturation</span>
            <div style={{ display: 'flex', gap: '3px' }}>
              {heatmaps?.workers?.map((w, idx) => (
                <div 
                  key={idx}
                  title={`${w.worker}: ${(w.value * 100).toFixed(1)}%`}
                  style={{ 
                    flex: 1, 
                    height: '14px', 
                    borderRadius: '2px',
                    background: `rgba(239, 68, 68, ${w.value})`,
                    border: '1px solid rgba(255,255,255,0.05)',
                    transition: 'all 0.2s'
                  }}
                />
              ))}
            </div>
          </div>

          {/* Queue Congestion */}
          <div style={{ marginBottom: '8px' }}>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block', marginBottom: '3px' }}>Queue Congestion</span>
            <div style={{ display: 'flex', gap: '3px' }}>
              {heatmaps?.queues?.map((q, idx) => (
                <div 
                  key={idx}
                  title={`${q.queue}: congestion level ${(q.value * 100).toFixed(1)}%`}
                  style={{ 
                    flex: 1, 
                    height: '14px', 
                    borderRadius: '2px',
                    background: `rgba(249, 115, 22, ${q.value})`,
                    border: '1px solid rgba(255,255,255,0.05)',
                    transition: 'all 0.2s'
                  }}
                />
              ))}
            </div>
          </div>

          {/* Stage Latency */}
          <div>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block', marginBottom: '3px' }}>Stage Latency</span>
            <div style={{ display: 'flex', gap: '3px' }}>
              {heatmaps?.stages?.map((s, idx) => (
                <div 
                  key={idx}
                  title={`${s.stage}: latency level ${(s.value * 100).toFixed(1)}%`}
                  style={{ 
                    flex: 1, 
                    height: '14px', 
                    borderRadius: '2px',
                    background: `rgba(59, 130, 246, ${s.value})`,
                    border: '1px solid rgba(255,255,255,0.05)',
                    transition: 'all 0.2s'
                  }}
                />
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* CENTER COLUMN: RECOMMENDATIONS & CRITICAL PATH OPTIMIZER */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', overflowY: 'auto', paddingRight: '4px' }}>
        <h4 style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-primary)', fontWeight: 600 }}>Actionable Recommendations</h4>
        
        {recommendations && recommendations.length > 0 ? (
          recommendations.map((r) => (
            <div 
              key={r.id} 
              style={{ 
                background: 'var(--bg-input)', 
                border: '1px solid var(--border-subtle)', 
                borderRadius: '4px', 
                padding: '10px',
                boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-accent)' }}>{r.title}</span>
                <span style={{ 
                  fontSize: '0.65rem', 
                  fontWeight: 600, 
                  color: r.confidence === 'high' ? 'var(--color-success)' : r.confidence === 'medium' ? 'var(--color-warning)' : 'var(--text-muted)'
                }}>
                  {r.confidence} confidence
                </span>
              </div>
              <p style={{ margin: '6px 0 0 0', fontSize: '0.7rem', color: 'var(--text-muted)', lineHeight: '1.3' }}>{r.description}</p>
              
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '8px', borderTop: '1px solid rgba(255,255,255,0.03)', paddingTop: '6px', fontSize: '0.65rem' }}>
                <span style={{ color: 'var(--text-muted)' }}>Estimated Gain:</span>
                <span style={{ fontWeight: 600, color: 'var(--color-success)' }}>-{(r.estimated_impact_ms / 1000.0).toFixed(2)}s</span>
              </div>
            </div>
          ))
        ) : (
          <div style={{ background: 'var(--bg-input)', padding: '12px', borderRadius: '4px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            No improvements recommended.
          </div>
        )}

        {/* Critical Path Optimizer Details */}
        <div style={{ background: 'var(--bg-input)', borderRadius: '6px', padding: '12px' }}>
          <h5 style={{ margin: '0 0 8px 0', fontSize: '0.8rem', color: 'var(--text-primary)', fontWeight: 600 }}>Critical Path Optimizer</h5>
          <p style={{ margin: '0 0 10px 0', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
            The sequential execution path limits maximum scaling. Parallelize stages to unlock performance gains.
          </p>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
            <span>CP Tasks Exec Duration:</span>
            <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
              {((baseline.critical_path_execution_ms || 0) / 1000.0).toFixed(2)}s
            </span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
            <span>CP Queue Latency:</span>
            <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
              {((baseline.critical_path_queue_wait_ms || 0) / 1000.0).toFixed(2)}s
            </span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: 'var(--text-muted)' }}>
            <span>Parallelization Index:</span>
            <span style={{ color: 'var(--color-success)', fontWeight: 600 }}>
              {((baseline.parallel_efficiency || 0) * 100).toFixed(1)}% efficiency
            </span>
          </div>
        </div>
      </div>

      {/* RIGHT COLUMN: WHAT-IF SIMULATOR HUD */}
      <div style={{ background: 'var(--bg-input)', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '16px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
        <h4 style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-primary)', fontWeight: 600 }}>What-If Simulation Sandbox</h4>
        
        {/* Sliders */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', marginBottom: '3px' }}>
              <span style={{ color: 'var(--text-muted)' }}>Worker Pool size</span>
              <span style={{ color: 'var(--color-accent)', fontWeight: 600 }}>{workers} workers</span>
            </div>
            <input 
              type="range" 
              min={1} 
              max={10} 
              step={1} 
              value={workers} 
              onChange={(e) => setWorkers(parseInt(e.target.value))} 
              style={{ width: '100%', cursor: 'pointer' }}
            />
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', marginBottom: '3px' }}>
              <span style={{ color: 'var(--text-muted)' }}>Stage Concurrency Limit</span>
              <span style={{ color: 'var(--color-accent)', fontWeight: 600 }}>{concurrency.toFixed(1)}x</span>
            </div>
            <input 
              type="range" 
              min={0.5} 
              max={4.0} 
              step={0.5} 
              value={concurrency} 
              onChange={(e) => setConcurrency(parseFloat(e.target.value))} 
              style={{ width: '100%', cursor: 'pointer' }}
            />
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', marginBottom: '3px' }}>
              <span style={{ color: 'var(--text-muted)' }}>Retry Rate Scaling</span>
              <span style={{ color: 'var(--color-accent)', fontWeight: 600 }}>{(retriesScale * 100).toFixed(0)}%</span>
            </div>
            <input 
              type="range" 
              min={0.0} 
              max={2.0} 
              step={0.25} 
              value={retriesScale} 
              onChange={(e) => setRetriesScale(parseFloat(e.target.value))} 
              style={{ width: '100%', cursor: 'pointer' }}
            />
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', marginBottom: '3px' }}>
              <span style={{ color: 'var(--text-muted)' }}>Queue Congestion Delay</span>
              <span style={{ color: 'var(--color-accent)', fontWeight: 600 }}>{(queueWaitScale * 100).toFixed(0)}%</span>
            </div>
            <input 
              type="range" 
              min={0.0} 
              max={2.0} 
              step={0.25} 
              value={queueWaitScale} 
              onChange={(e) => setQueueWaitScale(parseFloat(e.target.value))} 
              style={{ width: '100%', cursor: 'pointer' }}
            />
          </div>
        </div>

        {/* Comparison HUD Output */}
        {simulation && (
          <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '14px', marginTop: '4px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              <span>Pipeline Duration:</span>
              <div style={{ display: 'flex', gap: '8px' }}>
                <span style={{ textDecoration: 'line-through' }}>{((baseline.pipeline_duration_ms || 0)/1000.0).toFixed(2)}s</span>
                <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{(simulation.pipeline_duration_ms / 1000.0).toFixed(2)}s</span>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              <span>Critical Path Length:</span>
              <div style={{ display: 'flex', gap: '8px' }}>
                <span style={{ textDecoration: 'line-through' }}>{((baseline.critical_path_duration_ms || 0)/1000.0).toFixed(2)}s</span>
                <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{(simulation.critical_path_duration_ms / 1000.0).toFixed(2)}s</span>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              <span>Parallel Efficiency:</span>
              <div style={{ display: 'flex', gap: '8px' }}>
                <span style={{ textDecoration: 'line-through' }}>{((baseline.parallel_efficiency || 0)*100).toFixed(0)}%</span>
                <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{(simulation.parallel_efficiency * 100).toFixed(0)}%</span>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '6px', background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.2)', padding: '10px', borderRadius: '4px' }}>
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <span style={{ fontSize: '0.65rem', color: 'var(--color-success)', textTransform: 'uppercase', fontWeight: 600 }}>Total Saved Time</span>
                <span style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--color-success)' }}>
                  {(simulation.time_saved_ms / 1000.0).toFixed(2)}s
                </span>
              </div>
              <div style={{ textAlign: 'right' }}>
                <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', display: 'block' }}>Speedup</span>
                <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  +{simulation.percentage_improvement.toFixed(1)}%
                </span>
              </div>
            </div>
          </div>
        )}

        <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', background: 'var(--bg-panel-header)', padding: '6px 10px', borderRadius: '4px', lineHeight: '1.3' }}>
          <strong>Assumptions:</strong> Identical workload, unchanged sequential task durations, unchanged dependencies/DAG structure, variations apply strictly to execution resource properties.
        </div>
      </div>

    </div>
  );
};
