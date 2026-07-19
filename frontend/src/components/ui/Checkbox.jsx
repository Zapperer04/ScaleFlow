import React from 'react';

/**
 * Reusable Checkbox component.
 * 
 * @param {Object} props
 * @param {string} [props.label] - Field label text
 * @param {boolean} [props.checked=false] - Check state
 * @param {boolean} [props.disabled=false] - Disabled state
 * @param {string} [props.className=''] - Custom class overrides
 * @param {Function} [props.onChange] - Click listener
 */
export const Checkbox = ({
  label,
  checked = false,
  disabled = false,
  className = '',
  onChange,
  ...rest
}) => {
  return (
    <label className={`form-checkbox-label ${disabled ? 'disabled' : ''} ${className}`.trim()}>
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={onChange}
        className="form-checkbox-input"
        {...rest}
      />
      {label && <span className="form-checkbox-text">{label}</span>}
    </label>
  );
};
export default Checkbox;
