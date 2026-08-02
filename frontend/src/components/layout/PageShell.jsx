import React from 'react';
import PageHeader from './PageHeader';

/**
 * Reusable PageShell wrapper containing page max-width and layout standard padding.
 */
export const PageShell = ({ title, subtitle, actions, children }) => {
  return (
    <div className="page-shell-container">
      <PageHeader title={title} subtitle={subtitle} actions={actions} />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-24)' }}>
        {children}
      </div>
    </div>
  );
};

export default PageShell;
