import React from 'react';

/**
 * Reusable Input component.
 * 
 * @param {Object} props
 * @param {string} [props.type='text'] - Input type (text, password, number, email, etc.)
 * @param {string} [props.label] - Field label text
 * @param {string} [props.helperText] - Inline instructions or field details
 * @param {string} [props.error] - Validation error message
 * @param {boolean} [props.required=false] - Whether the field is required
 * @param {boolean} [props.disabled=false] - Whether the field is disabled
 * @param {string} [props.className=''] - Custom class overrides
 * @param {string} [props.placeholder] - Text placeholder value
 */
export const Input = ({
  type = 'text',
  label,
  helperText,
  error,
  required = false,
  disabled = false,
  className = '',
  placeholder,
  ...rest
}) => {
  const errorClass = error ? 'input-error' : '';
  
  const errorId = `${rest.id || 'input'}-error-msg`;
  const helperId = `${rest.id || 'input'}-helper-text`;
  
  return (
    <div className={`form-field-wrapper ${errorClass} ${className}`.trim()}>
      {label && (
        <label className="form-label" htmlFor={rest.id}>
          {label} {required && <span className="form-required-star" aria-hidden="true">*</span>}
        </label>
      )}
      <input
        type={type}
        disabled={disabled}
        placeholder={placeholder}
        className="form-input"
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
export default Input;
