import React from 'react';

/**
 * Reusable StatusBadge component featuring a semantic indicator dot.
 * 
 * @param {Object} props
 * @param {string} [props.status='online'] - Current state ('online', 'offline', 'checking', 'running', 'queued', 'completed', 'failed')
 * @param {string} [props.className=''] - Custom overrides
 * @param {React.ReactNode} props.children - Tag text
 */
export const StatusBadge = ({
  status = 'ready',
  className = '',
  children,
  ...rest
}) => {
  const normStatus = status.toLowerCase();
  
  // Map normalized status strings to CSS class names
  let badgeClass = 'badge';
  if (['running', 'queued', 'waiting', 'completed', 'paused', 'cancelled', 'failed', 'warning', 'ready'].includes(normStatus)) {
    badgeClass = `badge ${normStatus}`;
  } else if (normStatus === 'online') {
    badgeClass = 'badge completed';
  } else if (normStatus === 'offline') {
    badgeClass = 'badge failed';
  } else {
    badgeClass = 'badge queued';
  }

  return (
    <span className={`${badgeClass} ${className}`.trim()} {...rest}>
      <span className="status-badge-text">{children || status}</span>
    </span>
  );
};
export default StatusBadge;
