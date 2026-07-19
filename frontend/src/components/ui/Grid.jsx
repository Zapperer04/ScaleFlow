import React from 'react';

/**
 * Reusable CSS Grid layout primitive.
 * 
 * @param {Object} props
 * @param {number} [props.cols=1] - Number of layout grid columns
 * @param {string} [props.gap='16'] - Spacing key matching the spacing tokens
 * @param {string} [props.className=''] - Custom overrides
 * @param {React.ReactNode} props.children - Grid content elements
 */
export const Grid = ({
  cols = 1,
  gap = '16',
  className = '',
  children,
  ...rest
}) => {
  const gapValue = `var(--spacing-${gap})`;
  
  return (
    <div
      className={`layout-grid-primitive ${className}`.trim()}
      style={{
        display: 'grid',
        gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))`,
        gap: gapValue
      }}
      {...rest}
    >
      {children}
    </div>
  );
};
export default Grid;
