import React, { useEffect } from 'react';
import ReactDOM from 'react-dom';
import useDialog from '../../hooks/useDialog';

/**
 * Reusable Modal component utilizing React Portals.
 */
export const Modal = ({
  isOpen,
  onClose,
  title,
  className = '',
  children,
  ...rest
}) => {
  const containerRef = useDialog({ open: isOpen, onClose });

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

  const titleId = title ? 'modal-title-id' : undefined;

  return ReactDOM.createPortal(
    <div className="modal-overlay-backdrop" onClick={onClose} {...rest}>
      <div 
        ref={containerRef}
        className={`modal-card-box ${className}`.trim()} 
        onClick={e => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <div className="modal-card-header">
          {title && <h2 id={titleId} className="modal-title-text text-h2">{title}</h2>}
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
