import React, { useState, useRef, useEffect } from 'react';

/**
 * Reusable Popover component.
 * 
 * @param {Object} props
 * @param {React.ReactNode} props.trigger - Clickable trigger component
 * @param {string} [props.className=''] - Custom overrides
 * @param {React.ReactNode} props.children - Popover menu contents
 */
export const Popover = ({
  trigger,
  className = '',
  children,
  ...rest
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className={`popover-container ${className}`.trim()} ref={containerRef} {...rest}>
      <div className="popover-trigger-wrapper" onClick={() => setIsOpen(!isOpen)}>
        {trigger}
      </div>
      {isOpen && (
        <div className="popover-content-dropdown">
          {children}
        </div>
      )}
    </div>
  );
};
export default Popover;
