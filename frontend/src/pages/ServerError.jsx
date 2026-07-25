import React from 'react';
import Button from '../components/ui/Button';

export const ServerError = () => {
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
      <h1 style={{ fontSize: 'clamp(3rem, 10vw, 6rem)', color: 'var(--color-failure)', fontWeight: 'var(--font-weight-bold)' }}>
        500
      </h1>
      <div>
        <h2 style={{ fontSize: 'var(--font-size-2xl)', marginBottom: '8px' }}>Internal error</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)', maxWidth: '400px', margin: '0 auto' }}>
          An unexpected error occurred. Please contact administrator if this persists.
        </p>
      </div>
      <Button variant="primary" onClick={() => (window.location.href = '/')}>
        Return Home
      </Button>
    </div>
  );
};
export default ServerError;
