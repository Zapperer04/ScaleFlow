import React from 'react';
import Modal from './Modal';
import Button from './Button';

/**
 * Reusable Confirmation Dialog component.
 * 
 * @param {Object} props
 * @param {boolean} props.isOpen - Visibility trigger
 * @param {string} props.title - Action title header
 * @param {string} props.message - Descriptive text prompt
 * @param {string} [props.confirmText='Confirm'] - Label for confirm action
 * @param {string} [props.cancelText='Cancel'] - Label for cancel action
 * @param {string} [props.variant='primary'] - Confirm button style variant
 * @param {Function} props.onConfirm - Success trigger
 * @param {Function} props.onCancel - Cancel trigger
 * @param {boolean} [props.loading=false] - Lock confirm state
 */
export const ConfirmDialog = ({
  isOpen,
  title,
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  variant = 'primary',
  onConfirm,
  onCancel,
  loading = false,
  ...rest
}) => {
  return (
    <Modal isOpen={isOpen} onClose={onCancel} title={title} {...rest}>
      <div className="confirm-dialog-content">
        <p className="confirm-dialog-msg text-body" style={{ marginBottom: '20px', color: 'var(--text-secondary)' }}>
          {message}
        </p>
        <div className="confirm-dialog-actions" style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
          <Button variant="secondary" onClick={onCancel} disabled={loading}>
            {cancelText}
          </Button>
          <Button variant={variant} onClick={onConfirm} loading={loading}>
            {confirmText}
          </Button>
        </div>
      </div>
    </Modal>
  );
};
export default ConfirmDialog;
