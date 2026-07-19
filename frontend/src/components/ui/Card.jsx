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
  children,
  ...rest
}) => {
  return (
    <div className={`card-panel-wrapper ${className}`.trim()} {...rest}>
      {header && <div className="card-panel-header">{header}</div>}
      <div className="card-panel-body">{children}</div>
      {footer && <div className="card-panel-footer">{footer}</div>}
    </div>
  );
};
export default Card;
