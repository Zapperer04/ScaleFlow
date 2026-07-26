import React from 'react';

export const EmptyState = ({ icon: Icon, title, description, action }) => {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 'var(--spacing-32)',
        textAlign: 'center',
        border: '1px dashed var(--border-subtle)',
        borderRadius: 'var(--radius-10)',
        backgroundColor: 'rgba(0, 0, 0, 0.05)',
        minHeight: '180px',
      }}
    >
      {Icon && <Icon size={28} style={{ color: 'var(--text-muted)', marginBottom: 'var(--spacing-12)' }} />}
      <h4 style={{ fontSize: 'var(--font-size-base)', fontWeight: 600, margin: '0 0 6px 0', color: 'var(--text-primary)' }}>{title}</h4>
      <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', maxWidth: '280px', margin: '0 0 16px 0', lineHeight: 'var(--lh-relaxed)' }}>{description}</p>
      {action && <div>{action}</div>}
    </div>
  );
};
export default EmptyState;
