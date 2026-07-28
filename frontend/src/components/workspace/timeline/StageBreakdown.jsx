import React, { useState } from 'react';

export const StageBreakdown = ({ stages = [] }) => {
  const [sortKey, setSortKey] = useState('total_duration');
  const [sortOrder, setSortOrder] = useState('desc'); // 'asc' or 'desc'

  if (!stages || stages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-8 bg-slate-900 border border-slate-800 rounded-xl text-slate-400">
        <p className="text-sm font-medium">No stage breakdown data available</p>
      </div>
    );
  }

  const formatDuration = (ms) => {
    if (ms >= 1000) {
      return `${(ms / 1000).toFixed(2)}s`;
    }
    return `${ms}ms`;
  };

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortOrder('desc');
    }
  };

  const sortedStages = [...stages].sort((a, b) => {
    let valA = a[sortKey];
    let valB = b[sortKey];

    // Handle nested or complex sorting keys if necessary
    if (typeof valA === 'object' && valA !== null) valA = valA.duration_ms || 0;
    if (typeof valB === 'object' && valB !== null) valB = valB.duration_ms || 0;

    if (valA < valB) return sortOrder === 'asc' ? -1 : 1;
    if (valA > valB) return sortOrder === 'asc' ? 1 : -1;
    return 0;
  });

  const getSortIcon = (key) => {
    if (sortKey !== key) return '↕️';
    return sortOrder === 'asc' ? '▲' : '▼';
  };

  return (
    <div className="flex flex-col bg-slate-900/50 backdrop-blur border border-slate-800 rounded-xl p-6 shadow-xl overflow-hidden">
      <div className="mb-4">
        <h3 className="text-base font-semibold text-slate-200">Stage Breakdown</h3>
        <p className="text-xs text-slate-400 mt-1">
          Detailed performance breakdown grouped by pipeline task execution stage
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-800 text-left">
          <thead>
            <tr className="text-xs font-semibold uppercase tracking-wider text-slate-400 bg-slate-900/80">
              <th
                onClick={() => handleSort('stage')}
                className="py-3.5 px-4 cursor-pointer hover:text-slate-200 transition-colors select-none"
              >
                Stage {getSortIcon('stage')}
              </th>
              <th
                onClick={() => handleSort('count')}
                className="py-3.5 px-4 cursor-pointer hover:text-slate-200 transition-colors select-none text-right"
              >
                Count {getSortIcon('count')}
              </th>
              <th
                onClick={() => handleSort('average_duration')}
                className="py-3.5 px-4 cursor-pointer hover:text-slate-200 transition-colors select-none text-right"
              >
                Average {getSortIcon('average_duration')}
              </th>
              <th
                onClick={() => handleSort('median_duration')}
                className="py-3.5 px-4 cursor-pointer hover:text-slate-200 transition-colors select-none text-right"
              >
                Median {getSortIcon('median_duration')}
              </th>
              <th
                onClick={() => handleSort('p95_duration')}
                className="py-3.5 px-4 cursor-pointer hover:text-slate-200 transition-colors select-none text-right"
              >
                P95 {getSortIcon('p95_duration')}
              </th>
              <th
                onClick={() => handleSort('total_duration')}
                className="py-3.5 px-4 cursor-pointer hover:text-slate-200 transition-colors select-none text-right"
              >
                Total Duration {getSortIcon('total_duration')}
              </th>
              <th className="py-3.5 px-4 text-right">Slowest Task</th>
              <th className="py-3.5 px-4 text-right">Fastest Task</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800 text-sm text-slate-300">
            {sortedStages.map((stg) => (
              <tr key={stg.stage} className="hover:bg-slate-800/40 transition-colors">
                <td className="py-3 px-4 font-medium text-slate-200">{stg.stage}</td>
                <td className="py-3 px-4 text-right">{stg.count}</td>
                <td className="py-3 px-4 text-right">{formatDuration(stg.average_duration)}</td>
                <td className="py-3 px-4 text-right">{formatDuration(stg.median_duration)}</td>
                <td className="py-3 px-4 text-right">{formatDuration(stg.p95_duration)}</td>
                <td className="py-3 px-4 text-right font-semibold text-indigo-400">
                  {formatDuration(stg.total_duration)}
                </td>
                <td className="py-3 px-4 text-right text-xs">
                  <span className="text-slate-400">Task #{stg.slowest_task.task_id}</span>
                  <span className="ml-1.5 px-1.5 py-0.5 bg-rose-500/10 text-rose-400 rounded border border-rose-500/20 font-semibold">
                    {formatDuration(stg.slowest_task.duration_ms)}
                  </span>
                </td>
                <td className="py-3 px-4 text-right text-xs">
                  <span className="text-slate-400">Task #{stg.fastest_task.task_id}</span>
                  <span className="ml-1.5 px-1.5 py-0.5 bg-emerald-500/10 text-emerald-400 rounded border border-emerald-500/20 font-semibold">
                    {formatDuration(stg.fastest_task.duration_ms)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default StageBreakdown;
