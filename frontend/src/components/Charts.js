import React from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const COLORS = ['#8b5cf6', '#ec4899', '#06b6d4'];

export const ThroughputChart = ({ throughput }) => (
  <div className="panel large">
    <div className="panel-header">
      <h2>Task Throughput Analysis</h2>
      <span className="panel-subtitle">Completed tasks over time buckets</span>
    </div>
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={throughput}>
        <defs>
          <linearGradient id="colorThroughput" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="name" stroke="#9ca3af" />
        <YAxis stroke="#9ca3af" />
        <Tooltip contentStyle={{ background: '#1f2937', border: 'none', borderRadius: '4px', color: '#fff' }} />
        <Area type="monotone" dataKey="count" stroke="#8b5cf6" strokeWidth={3} fillOpacity={1} fill="url(#colorThroughput)" />
      </AreaChart>
    </ResponsiveContainer>
  </div>
);

export const WorkerLoadChart = ({ workerDistribution }) => (
  <div className="panel">
    <div className="panel-header">
      <h2>Worker Load Distribution</h2>
      <span className="panel-subtitle">Tasks per worker node</span>
    </div>
    <ResponsiveContainer width="100%" height={280}>
      <PieChart>
        <Pie
          data={workerDistribution}
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={90}
          paddingAngle={5}
          dataKey="value"
        >
          {workerDistribution.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip contentStyle={{ background: '#1f2937', border: 'none', borderRadius: '4px', color: '#fff' }} />
      </PieChart>
    </ResponsiveContainer>
    <div className="legend">
      {workerDistribution.map((worker, idx) => (
        <div key={idx} className="legend-item">
          <div className="legend-dot" style={{ background: COLORS[idx] }} />
          <span>{worker.name}: {worker.value}</span>
        </div>
      ))}
    </div>
  </div>
);
