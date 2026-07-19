import React from 'react';

/**
 * Reusable PageHeader component for standardizing top dashboard partitions.
 * 
 * @param {Object} props
 * @param {string} props.title - Action title header
 * @param {string} [props.subtitle] - Detailed sub-label text
 * @param {React.ReactNode} [props.actions] - Optional action buttons rendered on the right
 * @param {string} [props.className=''] - Custom overrides
 */
export const PageHeader = ({
  title,
  subtitle,
  actions,
  className = '',
  ...rest
}) => {
  return (
    <div className={`page-header-container ${className}`.trim()} {...rest} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', borderBottom: '1px solid var(--border-divider)', paddingBottom: '16px' }}>
      <div className="page-header-text-block">
        <h1 className="page-header-title text-h1" style={{ margin: 0, color: 'var(--text-primary)' }}>{title}</h1>
        {subtitle && <p className="page-header-subtitle text-body" style={{ margin: '4px 0 0 0', color: 'var(--text-secondary)' }}>{subtitle}</p>}
      </div>
      {actions && <div className="page-header-actions-block" style={{ display: 'flex', gap: '12px' }}>{actions}</div>}
    </div>
  );
};
export default PageHeader;
