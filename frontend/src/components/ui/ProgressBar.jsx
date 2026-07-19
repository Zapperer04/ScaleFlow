import React from 'react';

/**
 * Reusable ProgressBar indicator.
 * 
 * @param {Object} props
 * @param {number} [props.value=0] - Percentage complete (0 to 100)
 * @param {string} [props.variant='primary'] - Color theme ('primary', 'success', 'warning', 'danger')
 * @param {string} [props.className=''] - Custom overrides
 */
export const ProgressBar = ({
  value = 0,
  variant = 'primary',
  className = '',
  ...rest
}) => {
  const percentage = Math.max(0, Math.min(100, value));
  const variantClass = `progress-${variant}`;

  return (
    <div className={`progress-track-wrapper ${variantClass} ${className}`.trim()} {...rest}>
      <div
        className="progress-fill-indicator"
        style={{ width: `${percentage}%` }}
        role="progressbar"
        aria-valuenow={percentage}
        aria-valuemin="0"
        aria-valuemax="100"
      />
    </div>
  );
};
export default ProgressBar;
