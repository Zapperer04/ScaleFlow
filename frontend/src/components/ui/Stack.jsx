import React from 'react';

/**
 * Reusable Stack flex container.
 * 
 * @param {Object} props
 * @param {string} [props.direction='column'] - Flow layout direction ('row', 'column')
 * @param {string} [props.gap='16'] - Spacing key matching spacing scale (2, 4, 8, 12, 16, 20, 24, 32, 40, 48, 64)
 * @param {string} [props.align='stretch'] - Flex alignment
 * @param {string} [props.justify='flex-start'] - Flex distribution
 * @param {string} [props.className=''] - Custom overrides
 * @param {React.ReactNode} props.children - Stack elements
 */
export const Stack = ({
  direction = 'column',
  gap = '16',
  align = 'stretch',
  justify = 'flex-start',
  className = '',
  children,
  ...rest
}) => {
  const gapValue = `var(--spacing-${gap})`;
  
  return (
    <div
      className={`layout-stack-primitive ${className}`.trim()}
      style={{
        display: 'flex',
        flexDirection: direction,
        gap: gapValue,
        alignItems: align,
        justifyContent: justify
      }}
      {...rest}
    >
      {children}
    </div>
  );
};
export default Stack;
