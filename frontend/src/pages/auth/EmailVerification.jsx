import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Card from '../../components/ui/Card';
import Button from '../../components/ui/Button';
import { CheckCircle, RefreshCw } from 'lucide-react';

export const EmailVerification = () => {
  const navigate = useNavigate();
  const [verifying, setVerifying] = useState(true);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    // Simulate API email verification
    const timer = setTimeout(() => {
      setVerifying(false);
      setSuccess(true);
    }, 1500);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div
      style={{
        minHeight: 'calc(100vh - 70px)',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        padding: 'var(--spacing-32) var(--spacing-24)',
        maxWidth: 'var(--max-width-reading)',
        margin: '0 auto',
      }}
    >
      <Card style={{ width: '100%', maxWidth: '400px', textAlign: 'center' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-24)', alignItems: 'center' }}>
          {verifying ? (
            <>
              <RefreshCw size={48} className="animate-spin" style={{ color: 'var(--color-accent)' }} />
              <div>
                <h2 style={{ fontSize: 'var(--font-size-xl)', marginBottom: '8px' }}>Verifying your email</h2>
                <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)', margin: 0 }}>
                  Please standby while we register your confirmation token.
                </p>
              </div>
            </>
          ) : success ? (
            <>
              <CheckCircle size={48} style={{ color: 'var(--color-success)' }} />
              <div>
                <h2 style={{ fontSize: 'var(--font-size-xl)', marginBottom: '8px' }}>Email verified</h2>
                <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)', margin: 0 }}>
                  Your account has been fully validated and activated.
                </p>
              </div>
              <Button variant="primary" onClick={() => navigate('/login')} style={{ width: '100%' }}>
                Go to Login
              </Button>
            </>
          ) : (
            <>
              <div style={{ color: 'var(--color-failure)', fontSize: 'var(--font-size-xl)' }}>Verification Failed</div>
              <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)' }}>
                Your token is invalid or has expired.
              </p>
              <Button variant="secondary" onClick={() => navigate('/register')} style={{ width: '100%' }}>
                Register Again
              </Button>
            </>
          )}
        </div>
      </Card>
    </div>
  );
};
export default EmailVerification;
