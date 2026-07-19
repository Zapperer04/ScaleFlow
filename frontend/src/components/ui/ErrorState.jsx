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
  className = '',
  ...rest
}) => {
  return (
    <div className={`error-state-card ${className}`.trim()} {...rest}>
      <span className="error-state-alert-icon" aria-hidden="true">⚠️</span>
      <h3 className="error-state-title text-h3">{title}</h3>
      <p className="error-state-msg text-body">{message}</p>
      {onRetry && (
        <Button variant="danger" onClick={onRetry} className="error-state-retry-btn">
          Retry Action
        </Button>
      )}
    </div>
  );
};
export default ErrorState;
