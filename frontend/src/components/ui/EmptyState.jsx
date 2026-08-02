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
  size = 'md', // 'sm', 'md', 'lg'
  className = '',
  ...rest
}) => {
  const sizeStyles = {
    sm: { padding: 'var(--spacing-16)', gap: 'var(--spacing-8)' },
    md: { padding: 'var(--spacing-32)', gap: 'var(--spacing-12)' },
    lg: { padding: 'var(--spacing-48)', gap: 'var(--spacing-16)' }
  }[size];

  return (
    <div 
      className={`empty-state-card panel elevation-1 ${className}`.trim()} 
      style={{ 
        display: 'flex', 
        flexDirection: 'column', 
        alignItems: 'center', 
        justifyContent: 'center', 
        textAlign: 'center',
        ...sizeStyles 
      }} 
      {...rest}
    >
      {icon && <div className="empty-state-icon-container" style={{ fontSize: size === 'lg' ? '2.5rem' : '1.5rem', color: 'var(--text-secondary)' }}>{icon}</div>}
      <h3 className="text-card-title" style={{ margin: 0 }}>{title}</h3>
      <p className="text-caption" style={{ color: 'var(--text-secondary)', maxContent: '450px', margin: 0 }}>{message}</p>
      {action && <div className="empty-state-action-btn-container" style={{ marginTop: 'var(--spacing-8)' }}>{action}</div>}
    </div>
  );
};
export default EmptyState;
