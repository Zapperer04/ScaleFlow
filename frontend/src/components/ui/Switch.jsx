import React from 'react';

/**
 * Reusable Switch (Toggle Slider) component.
 * 
 * @param {Object} props
 * @param {string} [props.label] - Inline label text
 * @param {boolean} [props.checked=false] - Active state
 * @param {boolean} [props.disabled=false] - Disabled state
 * @param {string} [props.className=''] - Custom overrides
 * @param {Function} [props.onChange] - Click listener
 */
export const Switch = ({
  label,
  checked = false,
  disabled = false,
  className = '',
  onChange,
  ...rest
}) => {
  return (
    <label className={`form-switch-wrapper ${disabled ? 'disabled' : ''} ${className}`.trim()}>
      <div className="form-switch-track-container">
        <input
          type="checkbox"
          checked={checked}
          disabled={disabled}
          onChange={onChange}
          className="form-switch-input"
          {...rest}
        />
        <span className="form-switch-slider" />
      </div>
      {label && <span className="form-switch-label">{label}</span>}
    </label>
  );
};
export default Switch;
