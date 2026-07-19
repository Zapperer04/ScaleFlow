import React from 'react';

/**
 * Reusable Button component for the ScaleFlow Design System.
 * 
 * @param {Object} props
 * @param {string} [props.variant='secondary'] - The button style variant ('primary', 'secondary', 'danger', 'ghost', 'outline')
 * @param {boolean} [props.loading=false] - Whether the button is in a loading state
 * @param {boolean} [props.disabled=false] - Whether the button is disabled
 * @param {React.ReactNode} [props.iconLeft] - Optional icon component rendered on the left
 * @param {React.ReactNode} [props.iconRight] - Optional icon component rendered on the right
 * @param {string} [props.className=''] - Additional custom class names
 * @param {React.ReactNode} props.children - The button content
 * @param {Function} [props.onClick] - Click handler function
 */
export const Button = ({
  variant = 'secondary',
  loading = false,
  disabled = false,
  iconLeft,
  iconRight,
  className = '',
  children,
  onClick,
  ...rest
}) => {
  const isDisabled = disabled || loading;
  
  const variantClass = `btn-${variant}`;
  const loadingClass = loading ? 'btn-loading' : '';
  const combinedClassName = `btn ${variantClass} ${loadingClass} ${className}`.trim();

  return (
    <button
      className={combinedClassName}
      disabled={isDisabled}
      onClick={onClick}
      {...rest}
    >
      {loading && (
        <span className="btn-spinner" aria-hidden="true">
          <svg className="animate-spin" viewBox="0 0 24 24" fill="none" style={{ width: '1em', height: '1em' }}>
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        </span>
      )}
      {!loading && iconLeft && <span className="btn-icon-left">{iconLeft}</span>}
      <span className="btn-text">{children}</span>
      {!loading && iconRight && <span className="btn-icon-right">{iconRight}</span>}
    </button>
  );
};
export default Button;
