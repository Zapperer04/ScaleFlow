import React from 'react';

/**
 * Reusable Alert banner component.
 * 
 * @param {Object} props
 * @param {string} [props.variant='info'] - Semantic tone ('success', 'warning', 'danger', 'info')
 * @param {string} [props.title] - Bold header title
 * @param {string} [props.className=''] - Custom overrides
 * @param {Function} [props.onClose] - Close button handler
 * @param {React.ReactNode} props.children - Banner content message
 */
export const Alert = ({
  variant = 'info',
  title,
  className = '',
  onClose,
  children,
  ...rest
}) => {
  const variantClass = `alert-${variant}`;

  return (
    <div className={`alert-banner ${variantClass} ${className}`.trim()} role="alert" {...rest}>
      <div className="alert-content-wrapper">
        {title && <strong className="alert-title">{title}</strong>}
        <div className="alert-message">{children}</div>
      </div>
      {onClose && (
        <button className="alert-close-btn" onClick={onClose} aria-label="Dismiss alert">
          ✕
        </button>
      )}
    </div>
  );
};
export default Alert;
