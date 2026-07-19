import React, { useEffect } from 'react';

/**
 * Reusable Toast pop-up message component.
 * 
 * @param {Object} props
 * @param {string} [props.variant='info'] - Semantic tone ('success', 'warning', 'danger', 'info')
 * @param {string} props.message - Notification message
 * @param {number} [props.duration=5000] - Autoclose timing in ms (0 to disable auto close)
 * @param {Function} props.onClose - Action triggered when toast closes
 * @param {string} [props.className=''] - Custom classes
 */
export const Toast = ({
  variant = 'info',
  message,
  duration = 5000,
  onClose,
  className = '',
  ...rest
}) => {
  useEffect(() => {
    if (duration > 0 && onClose) {
      const timer = setTimeout(() => {
        onClose();
      }, duration);
      return () => clearTimeout(timer);
    }
  }, [duration, onClose]);

  const variantClass = `toast-${variant}`;

  return (
    <div className={`toast-card ${variantClass} ${className}`.trim()} role="status" {...rest}>
      <span className="toast-message">{message}</span>
      {onClose && (
        <button onClick={onClose} className="toast-close-btn" aria-label="Close notification">
          ✕
        </button>
      )}
    </div>
  );
};
export default Toast;
