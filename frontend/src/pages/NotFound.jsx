import React from 'react';
import Button from '../components/ui/Button';

export const NotFound = () => {
  return (
    <div
      style={{
        minHeight: 'calc(100vh - 140px)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        textAlign: 'center',
        padding: 'var(--spacing-32) var(--spacing-24)',
        gap: 'var(--spacing-24)',
      }}
    >
      <h1 style={{ fontSize: 'clamp(3rem, 10vw, 6rem)', color: 'var(--color-accent)', fontWeight: 'var(--font-weight-bold)' }}>
        404
      </h1>
      <div>
        <h2 style={{ fontSize: 'var(--font-size-2xl)', marginBottom: '8px' }}>Page not found</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)', maxWidth: '400px', margin: '0 auto' }}>
          The document segment or page you requested could not be located.
        </p>
      </div>
      <Button variant="primary" onClick={() => (window.location.href = '/')}>
        Return Home
      </Button>
    </div>
  );
};
export default NotFound;
