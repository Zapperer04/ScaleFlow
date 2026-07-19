import React from 'react';

/**
 * Reusable TextArea component.
 * 
 * @param {Object} props
 * @param {string} [props.label] - Field label text
 * @param {string} [props.helperText] - Field usage instructions
 * @param {string} [props.error] - Validation error details
 * @param {boolean} [props.required=false] - Mandatory state
 * @param {boolean} [props.disabled=false] - Disabled state
 * @param {number} [props.rows=3] - Row count height
 * @param {string} [props.className=''] - Custom class overrides
 */
export const TextArea = ({
  label,
  helperText,
  error,
  required = false,
  disabled = false,
  rows = 3,
  className = '',
  ...rest
}) => {
  const errorClass = error ? 'input-error' : '';

  const errorId = `${rest.id || 'textarea'}-error-msg`;
  const helperId = `${rest.id || 'textarea'}-helper-text`;

  return (
    <div className={`form-field-wrapper ${errorClass} ${className}`.trim()}>
      {label && (
        <label className="form-label" htmlFor={rest.id}>
          {label} {required && <span className="form-required-star" aria-hidden="true">*</span>}
        </label>
      )}
      <textarea
        disabled={disabled}
        rows={rows}
        className="form-input form-textarea"
        required={required}
        aria-invalid={error ? 'true' : 'false'}
        aria-describedby={error ? errorId : helperText ? helperId : undefined}
        {...rest}
      />
      {error && <span id={errorId} className="form-error-msg" role="alert">{error}</span>}
      {!error && helperText && <span id={helperId} className="form-helper-text">{helperText}</span>}
    </div>
  );
};
export default TextArea;
