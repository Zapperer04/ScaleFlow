import React from 'react';

/**
 * Reusable Radio component.
 * 
 * @param {Object} props
 * @param {string} [props.label] - Choice label text
 * @param {string} props.name - Common group name
 * @param {boolean} [props.checked=false] - Check state
 * @param {boolean} [props.disabled=false] - Disabled state
 * @param {string} [props.className=''] - Custom overrides
 */
export const Radio = ({
  label,
  name,
  checked = false,
  disabled = false,
  className = '',
  ...rest
}) => {
  return (
    <label className={`form-radio-label ${disabled ? 'disabled' : ''} ${className}`.trim()}>
      <input
        type="radio"
        name={name}
        checked={checked}
        disabled={disabled}
        className="form-radio-input"
        {...rest}
      />
      {label && <span className="form-radio-text">{label}</span>}
    </label>
  );
};
export default Radio;
