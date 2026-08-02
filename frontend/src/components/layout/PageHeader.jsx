import React from 'react';

/**
 * Reusable PageHeader component for ScaleFlow screens.
 * 
 * @param {Object} props
 * @param {string} props.title - Main header title
 * @param {string} [props.subtitle] - Explanatory subtitle
 * @param {React.ReactNode} [props.actions] - Action buttons aligned to the right
 */
export const PageHeader = ({ title, subtitle, actions }) => {
  return (
    <header className="page-header-row" role="banner">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-4)' }}>
        <h1 className="text-page-title">{title}</h1>
        {subtitle && <p className="text-caption" style={{ color: 'var(--text-secondary)', margin: 0 }}>{subtitle}</p>}
      </div>
      {actions && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-12)' }}>
          {actions}
        </div>
      )}
    </header>
  );
};

export default PageHeader;
