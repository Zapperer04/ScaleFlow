import React from 'react';
import Button from './Button';

/**
 * Reusable ErrorState component.
 * 
 * @param {Object} props
 * @param {string} props.title - Action title header
 * @param {string} props.message - Descriptive failure message
 * @param {Function} [props.onRetry] - Optional retry click action
 * @param {string} [props.className=''] - Custom overrides
 */
export const ErrorState = ({
  title,
  message,
  onRetry,
  variant = 'default', // 'default', 'connection-lost'
  className = '',
  ...rest
}) => {
  const isConnectionLost = variant === 'connection-lost';
  const displayTitle = isConnectionLost ? 'Connection Lost' : title;
  const displayMsg = isConnectionLost ? 'Please check your local service run scripts or internet access and try again.' : message;

  return (
    <div 
      className={`error-state-card panel elevation-1 ${className}`.trim()} 
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        padding: 'var(--spacing-32)',
        gap: 'var(--spacing-12)',
        borderColor: 'var(--color-failure)'
      }}
      {...rest}
    >
      <span className="error-state-alert-icon" style={{ fontSize: '2rem', color: 'var(--color-failure)' }} aria-hidden="true">
        {isConnectionLost ? '🔌' : '⚠️'}
      </span>
      <h3 className="text-card-title" style={{ margin: 0 }}>{displayTitle}</h3>
      <p className="text-caption" style={{ color: 'var(--text-secondary)', maxContent: '450px', margin: 0 }}>{displayMsg}</p>
      {onRetry && (
        <Button variant="danger" onClick={onRetry} style={{ marginTop: 'var(--spacing-8)' }}>
          Retry Action
        </Button>
      )}
    </div>
  );
};
export default ErrorState;
