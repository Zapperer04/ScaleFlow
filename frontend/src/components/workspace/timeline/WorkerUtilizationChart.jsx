import React from 'react';

export const WorkerUtilizationChart = ({ workers = [] }) => {
  if (!workers || workers.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-8 bg-slate-900 border border-slate-800 rounded-xl text-slate-400">
        <p className="text-sm font-medium">No worker utilization data available</p>
      </div>
    );
  }

  const formatDuration = (ms) => {
    if (ms >= 1000) {
      return `${(ms / 1000).toFixed(2)}s`;
    }
    return `${ms}ms`;
  };

  return (
    <div className="flex flex-col bg-slate-900/50 backdrop-blur border border-slate-800 rounded-xl p-6 shadow-xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-base font-semibold text-slate-200">Worker Utilization</h3>
          <p className="text-xs text-slate-400 mt-1">
            Distribution of busy vs idle time across pipeline execution
          </p>
        </div>
        <span className="px-2.5 py-1 bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 rounded-md text-xs font-semibold">
          {workers.length} Active Workers
        </span>
      </div>

      <div className="space-y-5">
        {workers.map((w) => {
          const u = w.utilization ?? 0;
          return (
            <div key={w.worker} className="flex flex-col space-y-2 group">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]" />
                  <span className="text-sm font-medium text-slate-300 group-hover:text-slate-100 transition-colors">
                    {w.worker}
                  </span>
                </div>
                <div className="flex items-center space-x-4">
                  <span className="text-xs text-slate-400">
                    Busy: <strong className="text-slate-300">{formatDuration(w.busy_ms)}</strong>
                  </span>
                  <span className="text-xs text-slate-400">
                    Idle: <strong className="text-slate-300">{formatDuration(w.idle_ms)}</strong>
                  </span>
                  <span className="text-sm font-bold text-indigo-400">{u.toFixed(1)}%</span>
                </div>
              </div>

              {/* Progress bar */}
              <div className="h-3 w-full bg-slate-800 rounded-full overflow-hidden p-[1px] border border-slate-700/50">
                <div
                  className="h-full rounded-full transition-all duration-500 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 shadow-[0_0_12px_rgba(99,102,241,0.4)]"
                  style={{ width: `${u}%` }}
                />
              </div>

              {/* Stats sub-row */}
              <div className="flex items-center justify-start space-x-6 text-[10px] text-slate-400 pl-4 mt-0.5">
                <span>
                  Tasks: <strong className="text-slate-300">{w.tasks}</strong>
                </span>
                <span>
                  Completed: <strong className="text-emerald-400">{w.tasks_completed}</strong>
                </span>
                {w.tasks_failed > 0 && (
                  <span>
                    Failed: <strong className="text-rose-400">{w.tasks_failed}</strong>
                  </span>
                )}
                {w.retry_count > 0 && (
                  <span>
                    Retries: <strong className="text-amber-400">{w.retry_count}</strong>
                  </span>
                )}
                {w.lease_expiry_count > 0 && (
                  <span>
                    Lease Expiries: <strong className="text-rose-400">{w.lease_expiry_count}</strong>
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default WorkerUtilizationChart;
