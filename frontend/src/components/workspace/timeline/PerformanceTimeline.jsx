import React, { useRef, useEffect } from 'react';
import { usePipeline } from '../../../contexts/PipelineContext';

export const PerformanceTimeline = () => {
  const {
    performanceModel,
    timelineZoom,
    setTimelineZoom,
    timelineOffset,
    setTimelineOffset,
    selectedPerformanceSpanId,
    setSelectedPerformanceSpanId
  } = usePipeline();

  const containerRef = useRef(null);

  const { timeline = [], lanes = [], summary = {} } = performanceModel?.performance || {};
  const pipelineDurationMs = summary.pipeline_duration_ms || 1000;

  // Zoom controls
  const handleZoomIn = () => {
    setTimelineZoom(prev => Math.min(10, prev * 1.5));
  };

  const handleZoomOut = () => {
    setTimelineZoom(prev => Math.max(0.001, prev / 1.5));
  };

  const handleResetZoom = () => {
    setTimelineZoom(0.05); // standard zoom
    setTimelineOffset(0);
  };

  const handleAutoFit = () => {
    if (containerRef.current) {
      const containerWidth = containerRef.current.clientWidth - 180; // subtract worker name column width
      if (containerWidth > 0) {
        const optimalZoom = containerWidth / pipelineDurationMs;
        setTimelineZoom(optimalZoom);
        setTimelineOffset(0);
      }
    }
  };

  const handleFitSelection = () => {
    if (!selectedPerformanceSpanId) return;
    const seg = timeline.find(s => s.segment_id === selectedPerformanceSpanId);
    if (seg && containerRef.current) {
      const containerWidth = containerRef.current.clientWidth - 180;
      if (containerWidth > 0 && seg.duration_ms > 0) {
        const optimalZoom = containerWidth / (seg.duration_ms * 1.5);
        setTimelineZoom(Math.min(10, optimalZoom));
        setTimelineOffset(seg.start_ms * optimalZoom - 20);
      }
    }
  };

  // Scroll handler for panning
  const handleScroll = (e) => {
    setTimelineOffset(e.target.scrollLeft);
  };

  // Synchronize horizontal scrolling
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollLeft = timelineOffset;
    }
  }, [timelineOffset]);

  if (!performanceModel || !performanceModel.performance) {
    return (
      <div className="flex flex-col items-center justify-center p-8 bg-slate-900 border border-slate-800 rounded-xl text-slate-400">
        <p className="text-sm font-medium">No performance timeline data available</p>
      </div>
    );
  }

  const formatTime = (ms) => {
    if (ms >= 1000) {
      return `${(ms / 1000).toFixed(2)}s`;
    }
    return `${ms}ms`;
  };

  return (
    <div className="flex flex-col bg-slate-900/50 backdrop-blur border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
      {/* Header with zoom controls */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h3 className="text-base font-semibold text-slate-200">Execution Timeline</h3>
          <p className="text-xs text-slate-400 mt-1">
            Deterministic execution waterfall across workers
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleZoomOut}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded border border-slate-700 transition-colors"
          >
            Zoom Out
          </button>
          <button
            onClick={handleZoomIn}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded border border-slate-700 transition-colors"
          >
            Zoom In
          </button>
          <button
            onClick={handleAutoFit}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-indigo-400 text-xs font-semibold rounded border border-slate-700 transition-colors"
          >
            Auto-fit
          </button>
          <button
            onClick={handleFitSelection}
            disabled={!selectedPerformanceSpanId}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-emerald-400 disabled:opacity-40 disabled:hover:bg-slate-800 text-xs font-semibold rounded border border-slate-700 transition-colors"
          >
            Fit Selection
          </button>
          <button
            onClick={handleResetZoom}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded border border-slate-700 transition-colors"
          >
            Reset
          </button>
        </div>
      </div>

      {/* Main timeline container */}
      <div className="border border-slate-800 rounded-lg overflow-hidden bg-slate-950/60">
        {/* Time Axis Header */}
        <div className="flex border-b border-slate-800 bg-slate-900/60 sticky top-0 z-10">
          <div className="w-[180px] min-w-[180px] px-4 py-2 text-xs font-semibold text-slate-400 border-r border-slate-800 bg-slate-900 select-none">
            Worker ID
          </div>
          <div className="flex-1 relative overflow-hidden h-8 select-none">
            {/* Render minor ticks on the time ruler */}
            {Array.from({ length: 11 }).map((_, idx) => {
              const fraction = idx / 10;
              const timeVal = fraction * pipelineDurationMs;
              const leftPos = timeVal * timelineZoom;
              return (
                <div
                  key={idx}
                  className="absolute bottom-0 text-[10px] text-slate-500 font-semibold border-l border-slate-800/80 pl-1 h-5 transform -translate-x-1/2"
                  style={{ left: `${leftPos}px` }}
                >
                  {formatTime(timeVal)}
                </div>
              );
            })}
          </div>
        </div>

        {/* Lanes List */}
        <div
          ref={containerRef}
          onScroll={handleScroll}
          className="flex-1 overflow-x-auto overflow-y-hidden max-h-[400px] divide-y divide-slate-800/60"
        >
          <div style={{ width: `${pipelineDurationMs * timelineZoom + 180}px` }}>
            {lanes.map((l) => {
              const laneSegs = timeline.filter(s => s.lane === l.lane);
              return (
                <div key={l.lane} className="flex relative items-stretch group min-h-[48px] hover:bg-slate-900/20">
                  {/* Worker Name Label */}
                  <div className="w-[180px] min-w-[180px] px-4 py-3 text-xs font-medium text-slate-300 border-r border-slate-800 bg-slate-950/40 select-none flex items-center">
                    {l.worker_id}
                  </div>

                  {/* Lane timeline bar container */}
                  <div className="flex-1 relative min-h-[48px] py-2">
                    {laneSegs.map((seg) => {
                      const leftPos = seg.start_ms * timelineZoom;
                      // Minimum width requirement: 1ms maps to at least 2px
                      const barWidth = Math.max(2, seg.duration_ms * timelineZoom);
                      const isSelected = selectedPerformanceSpanId === seg.segment_id;
                      
                      // Highlight queue wait if present
                      const queueLeft = (seg.start_ms - (seg.queue_wait_ms || 0)) * timelineZoom;
                      const queueWidth = (seg.queue_wait_ms || 0) * timelineZoom;

                      return (
                        <React.Fragment key={seg.segment_id}>
                          {/* Queue Wait Bar (if wait is valid and exists) */}
                          {seg.queue_wait_ms !== null && seg.queue_wait_ms > 0 && (
                            <div
                              className="absolute top-1/2 -translate-y-1/2 h-2 bg-indigo-500/20 border border-dashed border-indigo-500/40 rounded-sm cursor-pointer hover:border-indigo-400 transition-colors"
                              style={{
                                left: `${queueLeft}px`,
                                width: `${queueWidth}px`
                              }}
                              title={`Queue Wait: ${formatTime(seg.queue_wait_ms)}`}
                            />
                          )}

                          {/* Task execution block */}
                          <div
                            onClick={() => setSelectedPerformanceSpanId(seg.segment_id)}
                            className={`absolute top-1/2 -translate-y-1/2 h-6 rounded-md cursor-pointer flex items-center px-2 text-[10px] font-bold border transition-all select-none overflow-hidden text-ellipsis whitespace-nowrap
                              ${seg.status === 'completed'
                                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20 shadow-[0_0_8px_rgba(16,185,129,0.05)]'
                                : 'bg-rose-500/10 border-rose-500/30 text-rose-400 hover:bg-rose-500/20 shadow-[0_0_8px_rgba(244,63,94,0.05)]'
                              }
                              ${isSelected ? 'ring-2 ring-indigo-400 ring-offset-2 ring-offset-slate-950 border-indigo-400 scale-[1.02]' : ''}
                            `}
                            style={{
                              left: `${leftPos}px`,
                              width: `${barWidth}px`
                            }}
                          >
                            <span className="truncate">{`Task ${seg.task_id} (att ${seg.retry})`}</span>
                            {/* Hover tooltip details */}
                            <div className="hidden group-hover:block absolute bg-slate-900 border border-slate-700 text-slate-200 p-2 rounded shadow-lg text-[10px] -top-16 left-0 z-50 pointer-events-none">
                              <div>Task ID: {seg.task_id}</div>
                              <div>Worker: {seg.worker_id}</div>
                              <div>Queue: {seg.queue}</div>
                              <div>Duration: {formatTime(seg.duration_ms)}</div>
                              {seg.queue_wait_ms !== null && <div>Queue Wait: {formatTime(seg.queue_wait_ms)}</div>}
                              <div>Status: {seg.status}</div>
                            </div>
                          </div>
                        </React.Fragment>
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
  );
};

export default PerformanceTimeline;
