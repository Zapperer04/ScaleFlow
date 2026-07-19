import React from 'react';
import Grid from '../ui/Grid';

/**
 * Reusable grid layout for workspace cards.
 */
export const WorkspaceGrid = ({ cols = 1, children, className = '', ...rest }) => {
  return (
    <Grid cols={cols} gap="20" className={`workspace-grid ${className}`.trim()} {...rest}>
      {children}
    </Grid>
  );
};
export default WorkspaceGrid;
