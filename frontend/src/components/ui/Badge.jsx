import React from 'react';

/**
 * Reusable Badge component.
 * 
 * @param {Object} props
 * @param {string} [props.variant='info'] - Semantic variant style ('success', 'warning', 'danger', 'info')
 * @param {string} [props.className=''] - Custom overrides
 * @param {React.ReactNode} props.children - Label contents
 */
export const Badge = ({
  variant = 'info',
  className = '',
  children,
  ...rest
}) => {
  const variantClass = `badge-${variant}`;
  return (
    <span className={`badge ${variantClass} ${className}`.trim()} {...rest}>
      {children}
    </span>
  );
};
export default Badge;
