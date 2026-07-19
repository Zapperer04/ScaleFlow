import React from 'react';

/**
 * Reusable EmptyState component.
 * 
 * @param {Object} props
 * @param {string} props.title - Action title header
 * @param {string} props.message - Helpful description details
 * @param {React.ReactNode} [props.icon] - Optional centered icon representation
 * @param {React.ReactNode} [props.action] - Optional actionable button trigger
 * @param {string} [props.className=''] - Custom overrides
 */
export const EmptyState = ({
  title,
  message,
  icon,
  action,
  className = '',
  ...rest
}) => {
  return (
    <div className={`empty-state-card ${className}`.trim()} {...rest}>
      {icon && <div className="empty-state-icon-container">{icon}</div>}
      <h3 className="empty-state-title text-h3">{title}</h3>
      <p className="empty-state-msg text-body">{message}</p>
      {action && <div className="empty-state-action-btn-container">{action}</div>}
    </div>
  );
};
export default EmptyState;
