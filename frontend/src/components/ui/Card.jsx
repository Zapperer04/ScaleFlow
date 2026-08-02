import React from 'react';

/**
 * Reusable Card component.
 * 
 * @param {Object} props
 * @param {string} [props.className=''] - Custom overrides
 * @param {React.ReactNode} [props.header] - Optional header element
 * @param {React.ReactNode} [props.footer] - Optional footer element
 * @param {React.ReactNode} props.children - Main card body contents
 */
export const Card = ({
  className = '',
  header,
  footer,
  variant = 'primary', // 'primary' (bordered elevation-1), 'secondary' (elevation-2 flush layout)
  children,
  ...rest
}) => {
  const elevationClass = variant === 'primary' ? 'elevation-1' : 'elevation-2';
  return (
    <div className={`card-panel-wrapper panel ${elevationClass} ${className}`.trim()} {...rest}>
      {header && <div className="card-panel-header" style={{ marginBottom: 'var(--spacing-12)' }}>{header}</div>}
      <div className="card-panel-body">{children}</div>
      {footer && <div className="card-panel-footer" style={{ marginTop: 'var(--spacing-12)', borderTop: '1px solid var(--border-divider)', paddingTop: 'var(--spacing-12)' }}>{footer}</div>}
    </div>
  );
};
export default Card;
