import React, { useState } from 'react';

/**
 * Reusable Tooltip component.
 * 
 * @param {Object} props
 * @param {string} props.content - Text displayed on hover
 * @param {string} [props.position='top'] - Alignment anchor ('top', 'bottom', 'left', 'right')
 * @param {string} [props.className=''] - Custom overrides
 * @param {React.ReactNode} props.children - Target hover child component
 */
export const Tooltip = ({
  content,
  position = 'top',
  className = '',
  children,
  ...rest
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const positionClass = `tooltip-${position}`;

  return (
    <div
      className={`tooltip-trigger-container ${className}`.trim()}
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
      {...rest}
    >
      {children}
      {isVisible && (
        <span className={`tooltip-bubble ${positionClass}`} role="tooltip">
          {content}
        </span>
      )}
    </div>
  );
};
export default Tooltip;
