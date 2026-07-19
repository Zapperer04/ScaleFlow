import React from 'react';

/**
 * Reusable Panel layout container.
 * 
 * @param {Object} props
 * @param {string} [props.className=''] - Custom overrides
 * @param {React.ReactNode} props.children - Panel contents
 */
export const Panel = ({
  className = '',
  children,
  ...rest
}) => {
  return (
    <div className={`panel ${className}`.trim()} {...rest}>
      {children}
    </div>
  );
};
export default Panel;
