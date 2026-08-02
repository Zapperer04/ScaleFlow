import React, { useState, useMemo, useEffect } from 'react';
import { usePipeline } from '../../../contexts/PipelineContext';

export const SchedulingAdvisorTab = () => {
  const {
    advisorModel,
    advisorLoading,
    advisorError,
    setSelectedTaskId,
    selectedWorkerId,
    setSelectedWorkerId,
    performanceModel
  } = usePipeline();

  const advisorData = advisorModel?.advisor || {};
  const {
    worker_analysis = {},
    queue_analysis = {},
    autoscaling = [],
    recommendations = [],
    scheduling_score = {},
    simulation = {}
  } = advisorData;

  const baseline = useMemo(() => simulation?.baseline || {}, [simulation]);
  const coefficients = useMemo(() => simulation?.coefficients || {}, [simulation]);

  // Sliders state
  const [simWorkers, setSimWorkers] = useState(1);
  const [simConcurrency, setSimConcurrency] = useState(1.0);
  const [simRetry, setSimRetry] = useState(1.0);
  const [simQueue, setSimQueue] = useState(1.0);

  // Sync state with loaded baseline
  useEffect(() => {
    if (baseline.worker_count) {
      setSimWorkers(baseline.worker_count);
    } else if (performanceModel?.performance?.summary?.worker_count) {
      setSimWorkers(performanceModel.performance.summary.worker_count);
    }
  }, [baseline.worker_count, performanceModel]);

  // Local what-if simulation calculation
  const simResults = useMemo(() => {
    if (!baseline || Object.keys(baseline).length === 0) return null;

    const baseWorkers = baseline.worker_count || performanceModel?.performance?.summary?.worker_count || 1;
    
    const f_W = simWorkers / baseWorkers;
    const f_C = simConcurrency;
    const f_R = simRetry;
    const f_Q = simQueue;

    const cp_total = baseline.critical_path_ms || 1000.0;
    const base_duration = baseline.duration_ms || 1000.0;
    const base_queue_wait = baseline.queue_wait_ms || 0.0;
    
    // Coefficient factors
    const c_worker = coefficients.worker || 0.18;
    const c_retry = coefficients.retry || 0.85;
    const c_queue = coefficients.queue || 0.22;
    const c_concurrency = coefficients.concurrency || 0.35;

    // Simulated metrics
    const sim_critical_path_ms = Math.max(
      100.0,
      cp_total * (1 - c_worker * (f_W - 1)) * (1 - c_concurrency * (f_C - 1)) * (1 + c_retry * (f_R - 1) * 0.1)
    );

    const sim_queue_wait_ms = Math.max(
      0.0,
      base_queue_wait * f_Q * (1.0 / (f_W * f_C)) * (1 - c_queue * (f_W - 1))
    );

    const delta_cp = cp_total - sim_critical_path_ms;
    const sim_duration_ms = Math.max(
      100.0,
      base_duration - delta_cp + (sim_queue_wait_ms - base_queue_wait) * 0.5
    );

    const sim_utilization = Math.min(
      100.0,
      Math.max(
        0.0,
        baseline.utilization * (1.0 / f_W) * f_C * (1 - 0.1 * (f_R - 1))
      )
    );

    const time_saved_ms = Math.max(0.0, base_duration - sim_duration_ms);
    const pct_improvement = (time_saved_ms / base_duration) * 100.0;

    return {
      duration_ms: sim_duration_ms,
      critical_path_ms: sim_critical_path_ms,
      queue_wait_ms: sim_queue_wait_ms,
      utilization: sim_utilization,
      time_saved_ms,
      pct_improvement
    };
  }, [simWorkers, simConcurrency, simRetry, simQueue, baseline, coefficients, performanceModel]);

  if (advisorLoading) {
    return (
      <div className="flex items-center justify-center p-12 bg-slate-900/40 rounded-xl text-slate-400 space-x-3">
        <div className="w-5 h-5 border-2 border-slate-400 border-t-transparent rounded-full animate-spin" />
        <span className="text-sm font-medium">Generating scheduling advisor intelligence...</span>
      </div>
    );
  }

  if (advisorError) {
    return (
      <div className="p-8 bg-slate-900/40 border border-rose-950/40 rounded-xl text-rose-400 text-sm">
        <strong>Advisor Load Failed:</strong> {advisorError}
      </div>
    );
  }

  if (!advisorModel || !advisorModel.advisor) {
    return (
      <div className="p-8 bg-slate-900/40 border border-slate-800 rounded-xl text-slate-400 text-sm text-center">
        No scheduling advisor details available. Ensure pipeline replay completed successfully.
      </div>
    );
  }

  const formatDuration = (ms) => {
    if (!ms || ms === 0) return '0s';
    const totalSecs = ms / 1000;
    if (totalSecs < 60) {
      return `${totalSecs.toFixed(1)}s`;
    }
    const mins = Math.floor(totalSecs / 60);
    const secs = Math.round(totalSecs % 60);
    return `${mins}m ${secs}s`;
  };

  const getSeverityBadgeClass = (sev) => {
    switch (sev) {
      case 'critical': return 'bg-rose-500/10 text-rose-400 border-rose-500/20';
      case 'high': return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      case 'medium': return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20';
      default: return 'bg-sky-500/10 text-sky-400 border-sky-500/20';
    }
  };

  const selectRecommendation = (rec) => {
    if (rec.affected_tasks && rec.affected_tasks.length > 0) {
      setSelectedTaskId(rec.affected_tasks[0]);
    }
    if (rec.affected_workers && rec.affected_workers.length > 0) {
      setSelectedWorkerId(rec.affected_workers[0]);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', paddingBottom: '24px' }}>
      
      {/* 1. EXECUTIVE SUMMARY CARDS */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px' }}>
        <div style={{ padding: '16px', background: 'rgba(30, 41, 59, 0.4)', borderRadius: '12px', border: '1px solid var(--border-subtle)', textAlign: 'center' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>Scheduling Score</div>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: scheduling_score.score > 80 ? 'var(--color-success)' : scheduling_score.score > 50 ? 'var(--color-warning)' : 'var(--color-danger)' }}>
            {scheduling_score.score}/100
          </div>
          <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: '4px' }}>Current parallel eff: {scheduling_score.current_efficiency}%</div>
        </div>

        <div style={{ padding: '16px', background: 'rgba(30, 41, 59, 0.4)', borderRadius: '12px', border: '1px solid var(--border-subtle)', textAlign: 'center' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>Potential Score</div>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--color-accent)' }}>
            {Math.round(scheduling_score.potential_efficiency)}/100
          </div>
          <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: '4px' }}>With recommended changes</div>
        </div>

        <div style={{ padding: '16px', background: 'rgba(30, 41, 59, 0.4)', borderRadius: '12px', border: '1px solid var(--border-subtle)', textAlign: 'center' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>Estimated Time Saved</div>
          <div style={{ fontSize: '2.0rem', fontWeight: 'bold', color: 'var(--color-success)' }}>
            {formatDuration(scheduling_score.estimated_time_saved_ms)}
          </div>
          <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: '4px' }}>On top bottleneck chains</div>
        </div>

        <div style={{ padding: '16px', background: 'rgba(30, 41, 59, 0.4)', borderRadius: '12px', border: '1px solid var(--border-subtle)', textAlign: 'center' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>Active Recommendations</div>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--text-normal)' }}>
            {recommendations.length}
          </div>
          <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: '4px' }}>{worker_analysis.overloaded_workers} overloaded, {queue_analysis.congested_queues} congested</div>
        </div>
      </div>

      {/* 2. LOCAL WHAT-IF SIMULATOR */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '20px' }}>
        <div style={{ padding: '20px', background: 'var(--bg-panel)', borderRadius: '12px', border: '1px solid var(--border-subtle)', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <span style={{ fontSize: '0.85rem', fontWeight: 'bold', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '8px' }}>Local What-If Scheduler Simulator</span>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '4px' }}>
                <span>Worker Scaling (Active Pools): <strong>{simWorkers}</strong></span>
                <span style={{ color: 'var(--text-muted)' }}>Baseline: {baseline.worker_count || 1}</span>
              </div>
              <input type="range" min="1" max="32" value={simWorkers} onChange={(e) => setSimWorkers(parseInt(e.target.value))} style={{ width: '100%' }} />
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '4px' }}>
                <span>Concurrency Coeff: <strong>{simConcurrency.toFixed(1)}x</strong></span>
                <span style={{ color: 'var(--text-muted)' }}>Baseline: 1.0x</span>
              </div>
              <input type="range" min="0.5" max="3.0" step="0.1" value={simConcurrency} onChange={(e) => setSimConcurrency(parseFloat(e.target.value))} style={{ width: '100%' }} />
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '4px' }}>
                <span>Retry Backoff Scale: <strong>{simRetry.toFixed(1)}x</strong></span>
                <span style={{ color: 'var(--text-muted)' }}>Baseline: 1.0x</span>
              </div>
              <input type="range" min="0.0" max="2.0" step="0.1" value={simRetry} onChange={(e) => setSimRetry(parseFloat(e.target.value))} style={{ width: '100%' }} />
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '4px' }}>
                <span>Queue Wait Reducer: <strong>{Math.round(simQueue * 100)}%</strong></span>
                <span style={{ color: 'var(--text-muted)' }}>Baseline: 100%</span>
              </div>
              <input type="range" min="0.0" max="1.0" step="0.05" value={simQueue} onChange={(e) => setSimQueue(parseFloat(e.target.value))} style={{ width: '100%' }} />
            </div>
          </div>
        </div>

        {/* SIMULATED RESULTS */}
        {simResults && (
          <div style={{ padding: '20px', background: 'rgba(30, 41, 59, 0.25)', borderRadius: '12px', border: '1px solid var(--border-subtle)', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 'bold', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '8px' }}>Simulated Impact Output</span>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', height: '100%', alignContent: 'center' }}>
              <div>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Est. Pipeline Duration</div>
                <div style={{ fontSize: '1.25rem', fontWeight: 'bold', color: simResults.time_saved_ms > 0 ? 'var(--color-success)' : 'var(--text-normal)' }}>
                  {formatDuration(simResults.duration_ms)}
                </div>
                <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)' }}>Baseline: {formatDuration(baseline.duration_ms)}</div>
              </div>

              <div>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Predicted Improvement</div>
                <div style={{ fontSize: '1.25rem', fontWeight: 'bold', color: simResults.pct_improvement > 0 ? 'var(--color-success)' : 'var(--text-muted)' }}>
                  {simResults.pct_improvement.toFixed(1)}%
                </div>
                {simResults.time_saved_ms > 0 && (
                  <div style={{ fontSize: '0.6rem', color: 'var(--color-success)' }}>Saved {formatDuration(simResults.time_saved_ms)}</div>
                )}
              </div>

              <div>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Est. Queue Wait</div>
                <div style={{ fontSize: '1.1rem', fontWeight: 'bold', color: simResults.queue_wait_ms < baseline.queue_wait_ms ? 'var(--color-success)' : 'var(--text-normal)' }}>
                  {formatDuration(simResults.queue_wait_ms)}
                </div>
                <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)' }}>Baseline: {formatDuration(baseline.queue_wait_ms)}</div>
              </div>

              <div>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Est. Worker Utilization</div>
                <div style={{ fontSize: '1.1rem', fontWeight: 'bold' }}>
                  {simResults.utilization.toFixed(1)}%
                </div>
                <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)' }}>Baseline: {baseline.utilization}%</div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 3. AUTOSCALING ADVISOR & SCHEDULING RECOMMENDATIONS */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        
        {/* RECOMMENDATIONS */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <span style={{ fontSize: '0.85rem', fontWeight: 'bold' }}>Scheduling Recommendations</span>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '380px', overflowY: 'auto' }}>
            {recommendations.length === 0 ? (
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', padding: '16px', border: '1px dashed var(--border-subtle)', borderRadius: '8px', textAlign: 'center' }}>
                All scheduling configurations are healthy.
              </div>
            ) : (
              recommendations.map((rec) => (
                <div
                  key={rec.id}
                  onClick={() => selectRecommendation(rec)}
                  style={{
                    padding: '12px',
                    background: 'var(--bg-panel)',
                    borderRadius: '8px',
                    border: '1px solid var(--border-subtle)',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '6px',
                    transition: 'border-color 0.2s'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.borderColor = 'var(--color-accent)'}
                  onMouseLeave={(e) => e.currentTarget.style.borderColor = 'var(--border-subtle)'}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                      <span className={`px-2 py-0.5 text-[10px] font-bold uppercase rounded border ${getSeverityBadgeClass(rec.severity)}`}>
                        {rec.severity}
                      </span>
                      <span style={{ fontSize: '0.75rem', fontWeight: 'bold' }}>{rec.title}</span>
                    </div>
                    <span style={{ fontSize: '0.7rem', color: 'var(--color-success)', fontWeight: 'bold' }}>+{formatDuration(rec.estimated_gain_ms)}</span>
                  </div>
                  <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)', margin: 0 }}>{rec.description}</p>
                  
                  {rec.affected_tasks && rec.affected_tasks.length > 0 && (
                    <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                      Affected Tasks: {rec.affected_tasks.map(id => `Task-${id}`).join(', ')}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* AUTOSCALING PANEL */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <span style={{ fontSize: '0.85rem', fontWeight: 'bold' }}>Autoscaling Advice</span>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {autoscaling.length === 0 ? (
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', padding: '16px', border: '1px dashed var(--border-subtle)', borderRadius: '8px', textAlign: 'center' }}>
                No worker scaling required. Current allocations match demand.
              </div>
            ) : (
              autoscaling.map((scale, i) => (
                <div
                  key={i}
                  style={{
                    padding: '12px',
                    background: 'rgba(30, 41, 59, 0.2)',
                    borderRadius: '8px',
                    border: '1px solid var(--border-subtle)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}
                >
                  <div>
                    <div style={{ fontSize: '0.75rem', fontWeight: 'bold', display: 'flex', gap: '6px', alignItems: 'center' }}>
                      <span>Add {scale.worker_type.toUpperCase()} Worker</span>
                      <span style={{ fontSize: '0.65rem', padding: '1px 4px', background: 'var(--bg-panel)', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
                        Queue: {scale.queue}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                      Confidence: <strong style={{ color: scale.confidence === 'high' ? 'var(--color-success)' : 'var(--color-warning)' }}>{scale.confidence}</strong>
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '0.8rem', fontWeight: 'bold', color: 'var(--color-success)' }}>
                      -{formatDuration(scale.estimated_gain_ms)}
                    </div>
                    <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)' }}>Estimated Latency Saved</div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* 4. WORKER & QUEUE HEALTH */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '20px' }}>
        
        {/* WORKER HEALTH */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <span style={{ fontSize: '0.85rem', fontWeight: 'bold' }}>Worker Allocation Analysis</span>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', fontSize: '0.75rem', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)' }}>
                  <th style={{ padding: '6px' }}>Worker</th>
                  <th style={{ padding: '6px' }}>Busy Time</th>
                  <th style={{ padding: '6px' }}>Idle Time</th>
                  <th style={{ padding: '6px' }}>Utilization</th>
                  <th style={{ padding: '6px' }}>Queue Wait</th>
                  <th style={{ padding: '6px' }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {worker_analysis.workers?.map((w, i) => (
                  <tr
                    key={i}
                    onClick={() => setSelectedWorkerId(w.worker)}
                    style={{
                      borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                      cursor: 'pointer',
                      background: selectedWorkerId === w.worker ? 'rgba(59, 130, 246, 0.1)' : 'transparent'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.02)'}
                    onMouseLeave={(e) => e.currentTarget.style.backgroundColor = selectedWorkerId === w.worker ? 'rgba(59, 130, 246, 0.1)' : 'transparent'}
                  >
                    <td style={{ padding: '8px 6px', fontWeight: 'bold' }}>{w.worker}</td>
                    <td style={{ padding: '8px 6px' }}>{formatDuration(w.busy_ms)}</td>
                    <td style={{ padding: '8px 6px' }}>{formatDuration(w.idle_ms)}</td>
                    <td style={{ padding: '8px 6px' }}>{w.utilization}%</td>
                    <td style={{ padding: '8px 6px' }}>{formatDuration(w.queue_wait)}</td>
                    <td style={{ padding: '8px 6px' }}>
                      <span style={{
                        padding: '2px 6px',
                        borderRadius: '4px',
                        fontSize: '0.65rem',
                        fontWeight: 'bold',
                        background: w.status === 'overloaded' ? 'rgba(239, 68, 68, 0.15)' : w.status === 'idle' ? 'rgba(100, 116, 139, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                        color: w.status === 'overloaded' ? 'rgb(248, 113, 113)' : w.status === 'idle' ? 'rgb(148, 163, 184)' : 'rgb(52, 211, 153)'
                      }}>
                        {w.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* QUEUE HEALTH HEATMAP */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <span style={{ fontSize: '0.85rem', fontWeight: 'bold' }}>Queue Congestion Heatmap</span>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {queue_analysis.queues?.map((q, i) => (
              <div
                key={i}
                style={{
                  padding: '12px',
                  borderRadius: '8px',
                  border: '1px solid var(--border-subtle)',
                  background: q.severity === 'high' ? 'rgba(239, 68, 68, 0.08)' : q.severity === 'medium' ? 'rgba(245, 158, 11, 0.08)' : 'rgba(30, 41, 59, 0.3)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}
              >
                <div>
                  <div style={{ fontSize: '0.75rem', fontWeight: 'bold' }}>{q.queue}</div>
                  <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                    Max wait: <strong>{formatDuration(q.max_wait_ms)}</strong>
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 'bold', color: q.severity === 'high' ? 'rgb(248, 113, 113)' : q.severity === 'medium' ? 'rgb(251, 191, 36)' : 'var(--text-normal)' }}>
                    {formatDuration(q.average_wait_ms)} avg
                  </div>
                  <span style={{
                    fontSize: '0.6rem',
                    textTransform: 'uppercase',
                    fontWeight: 'bold',
                    color: q.severity === 'high' ? 'rgb(248, 113, 113)' : q.severity === 'medium' ? 'rgb(251, 191, 36)' : 'var(--text-muted)'
                  }}>
                    {q.severity} congestion
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>

    </div>
  );
};
