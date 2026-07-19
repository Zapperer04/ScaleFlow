import React from 'react';

/**
 * Reusable ButtonGroup container to layout a set of actions.
 * 
 * @param {Object} props
 * @param {string} [props.alignment='left'] - Button alignment ('left', 'center', 'right', 'stretch')
 * @param {string} [props.className=''] - Additional custom class names
 * @param {React.ReactNode} props.children - Button child elements
 */
export const ButtonGroup = ({
  alignment = 'left',
  className = '',
  children,
  ...rest
}) => {
  const alignmentClass = `btn-group-${alignment}`;
  return (
    <div className={`btn-group ${alignmentClass} ${className}`.trim()} {...rest}>
      {children}
    </div>
  );
};
export default ButtonGroup;
