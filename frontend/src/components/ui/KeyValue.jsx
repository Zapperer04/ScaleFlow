import React from 'react';

/**
 * Reusable KeyValue list row component.
 * 
 * @param {Object} props
 * @param {string} props.label - Choice label key
 * @param {React.ReactNode} props.value - Target details display
 * @param {string} [props.className=''] - Custom overrides
 */
export const KeyValue = ({
  label,
  value,
  className = '',
  ...rest
}) => {
  return (
    <div className={`key-value-row ${className}`.trim()} {...rest}>
      <span className="key-value-label text-caption">{label}</span>
      <span className="key-value-value text-body">{value}</span>
    </div>
  );
};
export default KeyValue;
