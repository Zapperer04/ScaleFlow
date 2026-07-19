import React from 'react';

/**
 * Reusable Skeleton loader for content placeholders.
 * 
 * @param {Object} props
 * @param {string} [props.variant='text'] - Shape style ('text', 'rect', 'circle')
 * @param {string} [props.width='100%'] - Placeholder width override
 * @param {string} [props.height='1rem'] - Placeholder height override
 * @param {string} [props.className=''] - Custom overrides
 */
export const Skeleton = ({
  variant = 'text',
  width = '100%',
  height = '1rem',
  className = '',
  ...rest
}) => {
  const shapeClass = `skeleton-${variant}`;
  return (
    <div
      className={`skeleton-loader ${shapeClass} ${className}`.trim()}
      style={{ width, height }}
      {...rest}
    />
  );
};
export default Skeleton;
