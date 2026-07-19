import React from 'react';
import Button from './Button';

/**
 * Reusable IconButton component for rendering icon-only buttons.
 * 
 * @param {Object} props
 * @param {React.ReactNode} props.icon - The icon element to render
 * @param {string} [props.variant='secondary'] - The button style variant
 * @param {boolean} [props.loading=false] - Whether the button is loading
 * @param {boolean} [props.disabled=false] - Whether the button is disabled
 * @param {string} [props.ariaLabel] - Required descriptive label for screen readers
 * @param {string} [props.className=''] - Additional class names
 * @param {Function} [props.onClick] - Click handler function
 */
export const IconButton = ({
  icon,
  variant = 'secondary',
  loading = false,
  disabled = false,
  ariaLabel,
  className = '',
  onClick,
  ...rest
}) => {
  return (
    <Button
      variant={variant}
      loading={loading}
      disabled={disabled}
      onClick={onClick}
      aria-label={ariaLabel}
      className={`btn-icon-only ${className}`.trim()}
      {...rest}
    >
      {icon}
    </Button>
  );
};
export default IconButton;
