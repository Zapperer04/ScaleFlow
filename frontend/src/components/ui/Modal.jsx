import React, { useEffect } from 'react';
import ReactDOM from 'react-dom';

/**
 * Reusable Modal component utilizing React Portals.
 * 
 * @param {Object} props
 * @param {boolean} props.isOpen - Whether the modal is active and visible
 * @param {Function} props.onClose - Action triggered when modal closes
 * @param {string} [props.title] - Modal header title
 * @param {string} [props.className=''] - Custom overrides
 * @param {React.ReactNode} props.children - Modal content contents
 */
export const Modal = ({
  isOpen,
  onClose,
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

  return ReactDOM.createPortal(
    <div className="modal-overlay-backdrop" onClick={onClose} {...rest}>
      <div className={`modal-card-box ${className}`.trim()} onClick={e => e.stopPropagation()}>
        <div className="modal-card-header">
          {title && <h2 className="modal-title-text text-h2">{title}</h2>}
          <button className="modal-close-button-icon" onClick={onClose} aria-label="Close modal">
            ✕
          </button>
        </div>
        <div className="modal-card-body">
          {children}
        </div>
      </div>
    </div>,
    document.body
  );
};
export default Modal;
