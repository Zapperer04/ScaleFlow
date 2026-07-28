import React from 'react';
import { usePipeline } from '../../../contexts/PipelineContext';

export const FlameGraph = () => {
  const {
    performanceModel,
    selectedPerformanceSpanId,
    setSelectedPerformanceSpanId
  } = usePipeline();

  if (!performanceModel || !performanceModel.performance) {
    return (
      <div className="flex flex-col items-center justify-center p-8 bg-slate-900 border border-slate-800 rounded-xl text-slate-400">
        <p className="text-sm font-medium">No performance flame graph data available</p>
      </div>
    );
  }

  const { flamegraph = [], summary = {} } = performanceModel.performance;
  const pipelineDurationMs = summary.pipeline_duration_ms || 1;

  const formatDuration = (ms) => {
    if (ms >= 1000) {
      return `${(ms / 1000).toFixed(2)}s`;
    }
    return `${ms}ms`;
  };

  // Group spans by depth to figure out how many rows to render
  const depths = Array.from(new Set(flamegraph.map(s => s.depth))).sort((a, b) => a - b);
  const maxDepth = depths.length > 0 ? depths[depths.length - 1] : 0;

  return (
    <div className="flex flex-col bg-slate-900/50 backdrop-blur border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
      <div>
        <h3 className="text-base font-semibold text-slate-200">Flame Graph Analytics</h3>
        <p className="text-xs text-slate-400 mt-1">
          Hierarchical execution paths representing relative duration and status
        </p>
      </div>

      {/* Flame Graph chart container */}
      <div className="border border-slate-800 rounded-lg p-4 bg-slate-950/60 overflow-x-auto">
        <div
          className="relative flex flex-col space-y-1.5 min-w-[600px] select-none"
          style={{ height: `${(maxDepth + 1) * 36 + 10}px` }}
        >
          {flamegraph.map((span, idx) => {
            const leftPct = (span.start_ms / pipelineDurationMs) * 100;
            const widthPct = (span.duration_ms / pipelineDurationMs) * 100;
            const topPos = span.depth * 36;
            
            const isSelected = selectedPerformanceSpanId === `task-${span.task_id}-attempt-0` || 
                               selectedPerformanceSpanId === `task-${span.task_id}-attempt-1` ||
                               selectedPerformanceSpanId === `task-${span.task_id}-attempt-2` ||
                               selectedPerformanceSpanId === `task-${span.task_id}-attempt-3`; // Fallback check or simple match

            const statusColors = span.status === 'completed'
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20 shadow-[0_0_6px_rgba(16,185,129,0.05)]'
              : 'bg-rose-500/10 border-rose-500/30 text-rose-400 hover:bg-rose-500/20 shadow-[0_0_6px_rgba(244,63,94,0.05)]';

            return (
              <div
                key={idx}
                onClick={() => setSelectedPerformanceSpanId(`task-${span.task_id}-attempt-0`)} // default to attempt 0 on flamegraph click
                className={`absolute h-8 rounded border text-[10px] font-semibold flex items-center justify-center cursor-pointer transition-all duration-200 group px-2 overflow-hidden text-ellipsis whitespace-nowrap
                  ${statusColors}
                  ${isSelected ? 'ring-2 ring-indigo-400 ring-offset-2 ring-offset-slate-950 border-indigo-400' : ''}
                `}
                style={{
                  left: `${leftPct}%`,
                  width: `${Math.max(1.5, widthPct)}%`,
                  top: `${topPos}px`
                }}
              >
                <span className="truncate">{`Task ${span.task_id}`}</span>

                {/* Flame graph tooltip */}
                <div className="absolute hidden group-hover:block bg-slate-900 border border-slate-700 text-slate-200 p-2.5 rounded-lg shadow-xl text-[10px] w-48 -top-24 left-1/2 transform -translate-x-1/2 z-50 pointer-events-none space-y-1">
                  <div className="font-semibold text-slate-100 border-b border-slate-800 pb-1 mb-1">
                    Task #{span.task_id}
                  </div>
                  <div>Worker: {span.worker_id}</div>
                  <div>Duration: {formatDuration(span.duration_ms)}</div>
                  {span.parent_task_id && <div>Parent: Task #{span.parent_task_id}</div>}
                  <div>Depth: {span.depth}</div>
                  <div>Status: {span.status}</div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default FlameGraph;
