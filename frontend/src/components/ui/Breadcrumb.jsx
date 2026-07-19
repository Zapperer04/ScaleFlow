import React from 'react';

/**
 * Reusable Breadcrumb navigation path.
 * 
 * @param {Object} props
 * @param {Array<{label: string, onClick?: Function}>} props.items - Navigation levels
 * @param {string} [props.className=''] - Custom overrides
 */
export const Breadcrumb = ({
  items = [],
  className = '',
  ...rest
}) => {
  return (
    <nav className={`breadcrumb-container ${className}`.trim()} aria-label="Breadcrumb" {...rest}>
      <ol className="breadcrumb-list" style={{ display: 'flex', listStyle: 'none', padding: 0, margin: 0 }}>
        {items.map((item, idx) => {
          const isLast = idx === items.length - 1;
          
          return (
            <li key={idx} className="breadcrumb-item" style={{ display: 'flex', alignItems: 'center' }}>
              {item.onClick && !isLast ? (
                <button
                  onClick={item.onClick}
                  className="breadcrumb-link-btn"
                  style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer', color: 'var(--color-accent)' }}
                >
                  {item.label}
                </button>
              ) : (
                <span className={`breadcrumb-label ${isLast ? 'active' : ''}`} style={{ color: isLast ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
                  {item.label}
                </span>
              )}
              {!isLast && (
                <span className="breadcrumb-separator" style={{ margin: '0 8px', color: 'var(--text-disabled)' }}>
                  /
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
};
export default Breadcrumb;
