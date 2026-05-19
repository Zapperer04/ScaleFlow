import React from 'react';

const MetricCard = ({ icon: Icon, label, value, trend, color, gradient }) => (
  <div className="metric-card" style={{ background: gradient }}>
    <div className="metric-header">
      <div className="metric-icon" style={{ background: color }}>
        <Icon size={20} strokeWidth={2.5} />
      </div>
      {trend > 0 && <span className="metric-trend">↑ {trend}%</span>}
    </div>
    <div className="metric-value">{value}</div>
    <div className="metric-label">{label}</div>
  </div>
);

export default MetricCard;
