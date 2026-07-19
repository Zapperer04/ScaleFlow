import React from 'react';

/**
 * Reusable Select dropdown component.
 * 
 * @param {Object} props
 * @param {string} [props.label] - Field label text
 * @param {Array<{value: string, label: string}>} props.options - List of menu options
 * @param {string} [props.error] - Validation error
 * @param {boolean} [props.required=false] - Mandatory state
 * @param {boolean} [props.disabled=false] - Disabled state
 * @param {string} [props.className=''] - Custom class overrides
 */
export const Select = ({
  label,
  options = [],
  error,
  required = false,
  disabled = false,
  className = '',
  ...rest
}) => {
  const errorClass = error ? 'input-error' : '';

  return (
    <div className={`form-field-wrapper ${errorClass} ${className}`.trim()}>
      {label && (
        <label className="form-label">
          {label} {required && <span className="form-required-star" aria-hidden="true">*</span>}
        </label>
      )}
      <select
        disabled={disabled}
        className="form-input form-select"
        required={required}
        {...rest}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {error && <span className="form-error-msg" role="alert">{error}</span>}
    </div>
  );
};
export default Select;
