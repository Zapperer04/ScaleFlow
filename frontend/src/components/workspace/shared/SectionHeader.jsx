import React from 'react';

export const SectionHeader = ({ title, badge, action }) => {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingBottom: 'var(--spacing-12)',
        borderBottom: '1px solid var(--border-divider)',
        marginBottom: 'var(--spacing-16)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-8)' }}>
        <h3
          style={{
            fontSize: 'var(--font-size-sm)',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: 'var(--text-primary)',
            margin: 0,
          }}
        >
          {title}
        </h3>
        {badge && (
          <span
            style={{
              padding: '2px 8px',
              fontSize: '10px',
              fontFamily: 'var(--font-mono)',
              fontWeight: 'bold',
              backgroundColor: 'var(--color-accent-glow)',
              border: '1px solid var(--color-accent)',
              borderRadius: 'var(--radius-6)',
              color: 'var(--color-accent)',
            }}
          >
            {badge}
          </span>
        )}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
};
export default SectionHeader;
