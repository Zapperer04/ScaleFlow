import React from 'react';

/**
 * Reusable Section layout block.
 * 
 * @param {Object} props
 * @param {string} [props.title] - Optional section title
 * @param {string} [props.className=''] - Custom overrides
 * @param {React.ReactNode} props.children - Section contents
 */
export const Section = ({
  title,
  className = '',
  children,
  ...rest
}) => {
  return (
    <section className={`layout-section-block ${className}`.trim()} {...rest}>
      {title && <h3 className="section-title text-h3">{title}</h3>}
      <div className="section-content">{children}</div>
    </section>
  );
};
export default Section;
