import React from 'react';
import Section from '../ui/Section';

/**
 * Reusable layout block section for document dashboard panels.
 */
export const WorkspaceSection = ({ title, children, className = '', ...rest }) => {
  return (
    <Section title={title} className={`workspace-section-block ${className}`.trim()} {...rest}>
      {children}
    </Section>
  );
};
export default WorkspaceSection;
