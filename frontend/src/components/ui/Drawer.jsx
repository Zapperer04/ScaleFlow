import React, { useEffect } from 'react';
import ReactDOM from 'react-dom';

/**
 * Reusable slide-out Drawer component.
 * 
 * @param {Object} props
 * @param {boolean} props.isOpen - Visibility trigger
 * @param {Function} props.onClose - Close action
 * @param {string} [props.placement='right'] - Position anchor ('left', 'right')
 * @param {string} [props.title] - Drawer header title
 * @param {string} [props.className=''] - Custom overrides
 * @param {React.ReactNode} props.children - Drawer content contents
 */
export const Drawer = ({
  isOpen,
  onClose,
  placement = 'right',
  title,
  className = '',
  children,
  ...rest
}) => {
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const placementClass = `drawer-${placement}`;

  return ReactDOM.createPortal(
    <div className="drawer-overlay-backdrop" onClick={onClose} {...rest}>
      <div className={`drawer-panel-box ${placementClass} ${className}`.trim()} onClick={e => e.stopPropagation()}>
        <div className="drawer-header">
          {title && <h3 className="drawer-title-text text-h3">{title}</h3>}
          <button className="drawer-close-button-icon" onClick={onClose} aria-label="Close drawer">
            ✕
          </button>
        </div>
        <div className="drawer-body">
          {children}
        </div>
      </div>
    </div>,
    document.body
  );
};
export default Drawer;
