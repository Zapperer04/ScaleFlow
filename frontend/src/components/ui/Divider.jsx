import React from 'react';

/**
 * Reusable Divider line.
 * 
 * @param {Object} props
 * @param {string} [props.className=''] - Custom overrides
 */
export const Divider = ({
  className = '',
  ...rest
}) => {
  return <div className={`divider ${className}`.trim()} role="separator" {...rest} />;
};
export default Divider;
