import React from 'react';

/**
 * Reusable Metric card component for displays.
 * 
 * @param {Object} props
 * @param {string} props.label - Metric label text
 * @param {string | number} props.value - Large numeric display value
 * @param {string} [props.className=''] - Custom overrides
 * @param {React.ReactNode} [props.change] - Optional delta indicator (e.g. +5%)
 */
export const Metric = React.memo(({
  label,
  value,
  className = '',
  change,
  ...rest
}) => {
  return (
    <div className={`metric-display-panel ${className}`.trim()} {...rest}>
      <span className="metric-label text-caption">{label}</span>
      <div className="metric-value-wrapper">
        <span className="metric-val text-h2">{value}</span>
        {change && <span className="metric-change-badge">{change}</span>}
      </div>
    </div>
  );
});
export default Metric;
