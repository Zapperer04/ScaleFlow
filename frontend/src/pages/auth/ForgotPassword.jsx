import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import Input from '../../components/ui/Input';
import Button from '../../components/ui/Button';
import Card from '../../components/ui/Card';
import { RefreshCw } from 'lucide-react';

export const ForgotPassword = () => {
  const { forgotPassword } = useAuth();
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState('idle'); // idle, loading, success, failure
  const [errorMsg, setErrorMsg] = useState('');
  const [validationError, setValidationError] = useState('');

  const validate = () => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setValidationError('Please enter a valid email.');
      return false;
    }
    setValidationError('');
    return true;
  };

  const handleSubmit = async (e) => {
    e?.preventDefault();
    if (!validate()) return;

    setStatus('loading');
    setErrorMsg('');

    try {
      await forgotPassword(email);
      setStatus('success');
    } catch (err) {
      setStatus('failure');
      setErrorMsg(err.message || 'Error executing request.');
    }
  };

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
      <Card style={{ width: '100%', maxWidth: '400px' }}>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-20)' }}>
          <div>
            <h2 style={{ fontSize: 'var(--font-size-2xl)', marginBottom: '8px' }}>Reset password</h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)', margin: 0 }}>
              Enter your email address and we will dispatch a password recovery link.
            </p>
          </div>

          {status === 'success' && (
            <div
              style={{
                padding: 'var(--spacing-12)',
                backgroundColor: 'rgba(16, 185, 129, 0.05)',
                border: '1px solid var(--color-success)',
                borderRadius: 'var(--radius-6)',
                color: 'var(--color-success)',
                fontSize: 'var(--font-size-xs)',
              }}
            >
              Reset link sent! Please check your email inbox to verify.
            </div>
          )}

          {status === 'failure' && (
            <div
              style={{
                padding: 'var(--spacing-12)',
                backgroundColor: 'rgba(244, 63, 94, 0.05)',
                border: '1px solid var(--color-failure)',
                borderRadius: 'var(--radius-6)',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
              }}
            >
              <div style={{ color: 'var(--color-failure)', fontSize: 'var(--font-size-xs)' }}>
                {errorMsg}
              </div>
              <button
                type="button"
                onClick={handleSubmit}
                style={{
                  alignSelf: 'flex-start',
                  background: 'none',
                  border: 'none',
                  color: 'var(--color-failure)',
                  fontSize: 'var(--font-size-xs)',
                  fontWeight: 'bold',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  padding: 0,
                }}
              >
                <RefreshCw size={12} /> Retry request
              </button>
            </div>
          )}

          <Input
            label="Email Address"
            id="email"
            type="email"
            placeholder="john@example.com"
            value={email}
            disabled={status === 'loading' || status === 'success'}
            onChange={(e) => setEmail(e.target.value)}
            error={validationError}
          />

          <Button
            type="submit"
            variant="primary"
            disabled={!email || status === 'loading' || status === 'success'}
            iconLeft={status === 'loading' && <RefreshCw size={14} className="animate-spin" />}
            style={{ width: '100%' }}
          >
            {status === 'loading' ? 'Requesting...' : 'Reset Password'}
          </Button>

          <div style={{ textAlign: 'center', fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)' }}>
            Back to{' '}
            <a href="/login" style={{ color: 'var(--color-accent)', fontWeight: 'var(--font-weight-medium)' }}>
              Login
            </a>
          </div>
        </form>
      </Card>
    </div>
  );
};
export default ForgotPassword;
