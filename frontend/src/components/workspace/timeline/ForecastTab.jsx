import React, { useRef, useEffect } from 'react';
import { usePipeline } from '../../../contexts/PipelineContext';

export const ForecastTab = () => {
  const {
    forecastModel,
    forecastLoading,
    forecastError,
    performanceModel,
    timelineZoom,
    setTimelineZoom,
    timelineOffset,
    setTimelineOffset,
    selectedPerformanceSpanId,
    setSelectedPerformanceSpanId,
    setSelectedTaskId
  } = usePipeline();

  const containerRef = useRef(null);

  // Sync scroll
  const handleScroll = (e) => {
    setTimelineOffset(e.target.scrollLeft);
  };

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollLeft = timelineOffset;
    }
  }, [timelineOffset]);

  if (forecastLoading) {
    return (
      <div className="flex items-center justify-center p-12 bg-slate-900/40 rounded-xl text-slate-400 space-x-3">
        <div className="w-5 h-5 border-2 border-slate-400 border-t-transparent rounded-full animate-spin" />
        <span className="text-sm font-medium">Generating operational execution forecast...</span>
      </div>
    );
  }

  if (forecastError) {
    return (
      <div className="p-8 bg-slate-900/40 border border-rose-950/40 rounded-xl text-rose-400 text-sm">
        <strong>Forecasting Failed:</strong> {forecastError}
      </div>
    );
  }

  if (!forecastModel || !forecastModel.forecast) {
    return (
      <div className="p-8 bg-slate-900/40 border border-slate-800 rounded-xl text-slate-400 text-sm text-center">
        No forecast data available for this pipeline.
      </div>
    );
  }

  const forecast = forecastModel.forecast;
  const perf = performanceModel?.performance || {};
  const timeline = perf.timeline || [];
  const lanes = perf.lanes || [];
  const futureTasks = forecast.future_tasks || [];

  const formatDuration = (ms) => {
    if (ms === 0) return '0s';
    const totalSecs = ms / 1000;
    if (totalSecs < 60) {
      return `${totalSecs.toFixed(1)}s`;
    }
    const mins = Math.floor(totalSecs / 60);
    const secs = Math.round(totalSecs % 60);
    return `${mins}m ${secs}s`;
  };

  const getWorkerIdForTask = (tid) => {
    const seg = timeline.find(s => s.task_id === tid);
    if (seg) return seg.worker_id;
    return lanes[0]?.worker_id || 'system';
  };

  // Find overall maximum time for timeline bounds
  const completedEnds = timeline.map(s => s.end_ms);
  const futureEnds = futureTasks.map(f => f.predicted_end_ms);
  const maxTimeMs = Math.max(...completedEnds, ...futureEnds, 1000);

  // Zoom controls
  const handleZoomIn = () => setTimelineZoom(prev => Math.min(10, prev * 1.5));
  const handleZoomOut = () => setTimelineZoom(prev => Math.max(0.001, prev / 1.5));
  const handleResetZoom = () => {
    setTimelineZoom(0.05);
    setTimelineOffset(0);
  };

  // SLA styling helpers
  const getSLAColor = (status) => {
    switch (status) {
      case 'On Track': return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
      case 'At Risk': return 'text-amber-400 bg-amber-500/10 border-amber-500/20';
      case 'Likely Miss': return 'text-rose-400 bg-rose-500/10 border-rose-500/20';
      default: return 'text-red-400 bg-red-500/10 border-red-500/20';
    }
  };

  return (
    <div className="flex flex-col gap-6 text-slate-200">
      
      {/* 1. Live Prediction Banner */}
      <div className={`p-4 rounded-xl border flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-gradient-to-r from-indigo-950/20 to-slate-900/40 border-indigo-500/15`}>
        <div className="flex items-center gap-3">
          <div className="w-3 h-3 rounded-full bg-indigo-400 animate-ping" />
          <div>
            <span className="text-xs uppercase font-bold tracking-widest text-indigo-400 block">Execution Forecast</span>
            <span className="text-base font-semibold">
              Pipeline expected to complete in{' '}
              <strong className="text-indigo-300 font-extrabold">{formatDuration(forecast.remaining_duration_ms)}</strong>
            </span>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-4 text-xs font-semibold">
          <div className="px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700/60">
            Confidence: <span className={forecast.confidence === 'High' ? 'text-emerald-400' : forecast.confidence === 'Medium' ? 'text-amber-400' : 'text-rose-400'}>{forecast.confidence}</span>
          </div>
          <div className={`px-3 py-1.5 rounded-lg border ${getSLAColor(forecast.sla_status)}`}>
            SLA: {forecast.sla_status}
          </div>
        </div>
      </div>

      {/* 2. Grid: ETA and SLA Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* ETA Card */}
        <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-5 flex flex-col justify-between">
          <div className="flex justify-between items-start mb-4">
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">Completion Estimate</h4>
              <p className="text-2xl font-bold mt-1 text-slate-100">{formatDuration(forecast.remaining_duration_ms)}</p>
            </div>
            <span className="text-xs font-medium text-slate-400 bg-slate-800 px-2 py-1 rounded">ETA</span>
          </div>
          <div className="space-y-2 text-xs border-t border-slate-800/60 pt-3">
            <div className="flex justify-between">
              <span className="text-slate-400">Current Progress</span>
              <span className="font-semibold text-slate-200">{forecast.progress.toFixed(1)}%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Estimated Finish Time</span>
              <span className="font-semibold text-slate-200">
                {new Date(forecast.estimated_finish).toLocaleTimeString()}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Confidence Level</span>
              <span className={`font-semibold ${forecast.confidence === 'High' ? 'text-emerald-400' : forecast.confidence === 'Medium' ? 'text-amber-400' : 'text-rose-400'}`}>
                {forecast.confidence}
              </span>
            </div>
          </div>
        </div>

        {/* SLA Card */}
        <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-5 flex flex-col justify-between">
          <div className="flex justify-between items-start mb-4">
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">SLA Monitoring</h4>
              <p className={`text-2xl font-bold mt-1 ${forecast.sla_status === 'On Track' ? 'text-emerald-400' : forecast.sla_status === 'At Risk' ? 'text-amber-400' : 'text-rose-400'}`}>
                {forecast.sla_status}
              </p>
            </div>
            <span className="text-xs font-medium text-slate-400 bg-slate-800 px-2 py-1 rounded">SLA</span>
          </div>
          <div className="space-y-2 text-xs border-t border-slate-800/60 pt-3">
            <div className="flex justify-between">
              <span className="text-slate-400">Remaining Buffer</span>
              <span className="font-semibold text-emerald-400">{formatDuration(forecast.remaining_buffer)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Expected Overrun</span>
              <span className={`font-semibold ${forecast.expected_overrun > 0 ? 'text-rose-400' : 'text-slate-400'}`}>
                {formatDuration(forecast.expected_overrun)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Current Bottleneck</span>
              <span className="font-semibold text-amber-400 max-w-[180px] truncate" title={forecast.current_bottleneck}>
                {forecast.current_bottleneck}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* 3. Remaining Critical Path Timeline Overlay */}
      <div className="bg-slate-900/30 border border-slate-800/80 rounded-xl p-5 space-y-4">
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">Remaining Critical Path</h4>
          <p className="text-xs text-slate-500 mt-1">Sequential future tasks determining the bottleneck threshold</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {forecast.critical_path.completed_tasks.map((tid) => (
            <React.Fragment key={tid}>
              <div 
                onClick={() => setSelectedTaskId(tid)}
                className="px-2.5 py-1.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-lg text-xs font-semibold cursor-pointer hover:bg-emerald-500/20 transition-all select-none"
              >
                Task {tid} (Done)
              </div>
              <span className="text-slate-600">➔</span>
            </React.Fragment>
          ))}
          {forecast.critical_path.remaining_tasks.map((tid, idx) => {
            const isLast = idx === forecast.critical_path.remaining_tasks.length - 1;
            const isRun = timeline.some(s => s.task_id === tid && s.status === 'running');
            return (
              <React.Fragment key={tid}>
                <div 
                  onClick={() => setSelectedTaskId(tid)}
                  className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold cursor-pointer transition-all select-none border border-dashed
                    ${isRun 
                      ? 'bg-blue-500/10 border-blue-500/30 text-blue-400 hover:bg-blue-500/20 animate-pulse' 
                      : 'bg-amber-500/10 border-amber-500/30 text-amber-400 hover:bg-amber-500/20'
                    }`}
                >
                  Task {tid} (Predicted)
                </div>
                {!isLast && <span className="text-slate-600">➔</span>}
              </React.Fragment>
            );
          })}
          {forecast.critical_path.remaining_tasks.length === 0 && (
            <span className="text-xs text-slate-500">Critical path fully completed.</span>
          )}
        </div>
      </div>

      {/* 4. Forecast Timeline with Dashed Overlay */}
      <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-5 space-y-4">
        <div className="flex justify-between items-center flex-wrap gap-4">
          <div>
            <h4 className="text-sm font-semibold text-slate-200">Forecast Waterfall Timeline</h4>
            <p className="text-xs text-slate-400 mt-1">Dashed intervals indicate predicted execution segments</p>
          </div>
          <div className="flex items-center gap-1.5">
            <button onClick={handleZoomOut} className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded border border-slate-700">Zoom Out</button>
            <button onClick={handleZoomIn} className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded border border-slate-700">Zoom In</button>
            <button onClick={handleResetZoom} className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded border border-slate-700">Reset</button>
          </div>
        </div>

        {/* Timeline body */}
        <div className="border border-slate-800 rounded-lg overflow-hidden bg-slate-950/60">
          {/* Ruler */}
          <div className="flex border-b border-slate-800 bg-slate-900/60 h-8 items-center relative select-none">
            <div className="w-[160px] min-w-[160px] px-4 text-xs font-semibold text-slate-400 border-r border-slate-800 bg-slate-900">
              Worker ID
            </div>
            <div className="flex-1 relative overflow-hidden h-full">
              {Array.from({ length: 11 }).map((_, idx) => {
                const fraction = idx / 10;
                const timeVal = fraction * maxTimeMs;
                const leftPos = timeVal * timelineZoom;
                return (
                  <div
                    key={idx}
                    className="absolute bottom-0 text-[9px] text-slate-500 border-l border-slate-800/80 pl-1 h-5 transform -translate-x-1/2"
                    style={{ left: `${leftPos}px` }}
                  >
                    {formatDuration(timeVal)}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Lanes */}
          <div ref={containerRef} onScroll={handleScroll} className="overflow-x-auto divide-y divide-slate-800/60">
            <div style={{ width: `${maxTimeMs * timelineZoom + 160}px` }}>
              {lanes.map((l) => {
                const laneSegs = timeline.filter(s => s.lane === l.lane);
                const laneFuture = futureTasks.filter(f => getWorkerIdForTask(f.task_id) === l.worker_id);

                return (
                  <div key={l.lane} className="flex relative items-stretch group min-h-[48px] hover:bg-slate-900/10">
                    <div className="w-[160px] min-w-[160px] px-4 py-3 text-xs font-medium text-slate-400 border-r border-slate-800 bg-slate-950/40 select-none flex items-center">
                      {l.worker_id}
                    </div>
                    <div className="flex-1 relative min-h-[48px] py-2">
                      {/* Completed/Running historical segments */}
                      {laneSegs.map((seg) => {
                        const leftPos = seg.start_ms * timelineZoom;
                        const barWidth = Math.max(4, seg.duration_ms * timelineZoom);
                        const isSelected = selectedPerformanceSpanId === seg.segment_id;
                        
                        return (
                          <div
                            key={seg.segment_id}
                            onClick={() => {
                              setSelectedPerformanceSpanId(seg.segment_id);
                              setSelectedTaskId(seg.task_id);
                            }}
                            className={`absolute top-1/2 -translate-y-1/2 h-6 rounded px-2 text-[9px] font-bold border transition-all cursor-pointer flex items-center select-none truncate
                              ${seg.status === 'completed'
                                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20'
                                : 'bg-blue-500/10 border-blue-500/30 text-blue-400 hover:bg-blue-500/20 animate-pulse'
                              }
                              ${isSelected ? 'ring-1 ring-indigo-400 border-indigo-400 scale-[1.01]' : ''}`}
                            style={{ left: `${leftPos}px`, width: `${barWidth}px` }}
                            title={`Task ${seg.task_id} (${seg.status}) - ${formatDuration(seg.duration_ms)}`}
                          >
                            T{seg.task_id} (att {seg.retry})
                          </div>
                        );
                      })}

                      {/* Predicted future segments */}
                      {laneFuture.map((f) => {
                        const leftPos = f.predicted_start_ms * timelineZoom;
                        const barWidth = Math.max(4, f.predicted_duration_ms * timelineZoom);
                        
                        return (
                          <div
                            key={f.task_id}
                            onClick={() => setSelectedTaskId(f.task_id)}
                            className={`absolute top-1/2 -translate-y-1/2 h-6 rounded px-2 text-[9px] font-bold border border-dashed transition-all cursor-pointer flex items-center select-none truncate
                              ${f.is_critical 
                                ? 'bg-amber-500/5 border-amber-500/40 text-amber-400 hover:bg-amber-500/15'
                                : 'bg-slate-800/10 border-slate-700/60 text-slate-400 hover:bg-slate-800/30'}`}
                            style={{ left: `${leftPos}px`, width: `${barWidth}px` }}
                            title={`[Forecasted] Task ${f.task_id} (${f.task_type}) - Expected: ${formatDuration(f.predicted_duration_ms)}`}
                          >
                            T{f.task_id} (predicted)
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* 5. Worker utilization forecasts */}
      <div className="space-y-3">
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">Worker Utilization Forecasts</h4>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {forecast.worker_forecasts.map((wf) => (
            <div key={wf.worker} className="bg-slate-900/40 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
              <div>
                <span className="text-xs font-semibold text-slate-300 block">{wf.worker}</span>
                <div className="flex justify-between items-baseline mt-2">
                  <span className="text-xs text-slate-500">Predicted Utilization</span>
                  <span className="text-lg font-bold text-indigo-400">{wf.predicted_utilization}%</span>
                </div>
                <div className="w-full bg-slate-950 h-1.5 rounded-full mt-1.5 overflow-hidden">
                  <div className="bg-indigo-500 h-full rounded-full" style={{ width: `${wf.predicted_utilization}%` }} />
                </div>
              </div>
              <div className="text-[10px] text-slate-400 mt-4 border-t border-slate-800/50 pt-2 flex justify-between">
                <span>Current Util: {wf.current_utilization}%</span>
                <span>Finish: {new Date(wf.likely_finish).toLocaleTimeString()}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 6. Stage forecast Table */}
      <div className="space-y-3 bg-slate-900/30 border border-slate-800/80 rounded-xl p-5">
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">Stage Progress & Predictions</h4>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs divide-y divide-slate-800">
            <thead>
              <tr className="text-slate-400 font-semibold">
                <th className="py-2.5">Stage</th>
                <th className="py-2.5">Progress</th>
                <th className="py-2.5">Predicted Remaining</th>
                <th className="py-2.5">Predicted Stage ETA</th>
                <th className="py-2.5">Confidence</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {forecast.stage_forecasts.map((sf) => (
                <tr key={sf.stage} className={sf.is_critical ? 'bg-amber-500/5' : ''}>
                  <td className="py-3 font-medium flex items-center gap-1.5">
                    {sf.stage}
                    {sf.is_critical && (
                      <span className="text-[9px] uppercase font-bold tracking-widest text-amber-500 border border-amber-500/20 bg-amber-500/10 px-1 rounded">
                        Critical
                      </span>
                    )}
                  </td>
                  <td className="py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-12 bg-slate-950 h-1.5 rounded-full overflow-hidden">
                        <div className="bg-emerald-500 h-full rounded-full" style={{ width: `${sf.progress}%` }} />
                      </div>
                      <span>{sf.progress}%</span>
                    </div>
                  </td>
                  <td className="py-3">{formatDuration(sf.remaining_ms)}</td>
                  <td className="py-3">{new Date(sf.eta).toLocaleTimeString()}</td>
                  <td className="py-3 font-semibold text-slate-400">{sf.confidence}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 7. Prediction Assumptions Banner */}
      <div className="p-3.5 rounded-lg border border-slate-800 bg-slate-950/40 text-[10px] text-slate-500">
        <strong>Prediction Assumptions:</strong> Forecasting models are calculated deterministically under the assumptions that the DAG structure is static, the worker pool remains unchanged, optimization guidance is currently disabled, retry configurations are immutable, and task duration probability distributions follow historically recorded models.
      </div>
      
      {/* Bottleneck animation styles */}
      <style>{`
        @keyframes pulse-bottleneck {
          0% { stroke: #ef4444; filter: drop-shadow(0 0 2px rgba(239, 68, 68, 0.4)); }
          50% { stroke: #f87171; filter: drop-shadow(0 0 8px rgba(239, 68, 68, 0.8)); }
          100% { stroke: #ef4444; filter: drop-shadow(0 0 2px rgba(239, 68, 68, 0.4)); }
        }
      `}</style>
    </div>
  );
};

export default ForecastTab;
