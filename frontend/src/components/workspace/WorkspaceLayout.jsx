import React from 'react';

/**
 * Reusable layout block container specifically for the document-centric workspace.
 */
export const WorkspaceLayout = ({ children, className = '', ...rest }) => {
  return (
    <div className={`workspace-layout-container ${className}`.trim()} {...rest} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-24)' }}>
      {children}
    </div>
  );
};
export default WorkspaceLayout;
