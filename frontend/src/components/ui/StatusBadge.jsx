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
  status = 'online',
  className = '',
  children,
  ...rest
}) => {
  let statusClass = 'checking';
  if (status === 'online' || status === 'completed') statusClass = 'online';
  if (status === 'offline' || status === 'failed') statusClass = 'offline';
  if (status === 'checking' || status === 'running' || status === 'queued') statusClass = 'checking';

  return (
    <span className={`status-badge-wrapper ${className}`.trim()} {...rest}>
      <span className={`status-dot ${statusClass}`} aria-hidden="true" />
      <span className="status-badge-text">{children}</span>
    </span>
  );
};
export default StatusBadge;
