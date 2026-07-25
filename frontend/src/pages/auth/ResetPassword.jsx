import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import Input from '../../components/ui/Input';
import Button from '../../components/ui/Button';
import Card from '../../components/ui/Card';
import { RefreshCw } from 'lucide-react';

export const ResetPassword = () => {
  const { resetPassword } = useAuth();
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [status, setStatus] = useState('idle'); // idle, loading, success, failure
  const [errorMsg, setErrorMsg] = useState('');
  const [validationErrors, setValidationErrors] = useState({});

  const validate = () => {
    const errs = {};
    if (password.length < 6) {
      errs.password = 'Password must be at least 6 characters.';
    }
    if (password !== confirmPassword) {
      errs.confirmPassword = 'Passwords do not match.';
    }
    setValidationErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e) => {
    e?.preventDefault();
    if (!validate()) return;

    setStatus('loading');
    setErrorMsg('');

    try {
      await resetPassword(password);
      setStatus('success');
      setTimeout(() => {
        window.location.href = '/login';
      }, 1000);
    } catch (err) {
      setStatus('failure');
      setErrorMsg(err.message || 'Error occurred during reset.');
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
            <h2 style={{ fontSize: 'var(--font-size-2xl)', marginBottom: '8px' }}>Create new password</h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)', margin: 0 }}>
              Specify a secure, distinct password of at least 6 characters.
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
              Password updated successfully! Redirecting to login...
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
                <RefreshCw size={12} /> Retry Update
              </button>
            </div>
          )}

          <Input
            label="New Password"
            id="password"
            type="password"
            placeholder="••••••••"
            value={password}
            disabled={status === 'loading' || status === 'success'}
            onChange={(e) => setPassword(e.target.value)}
            error={validationErrors.password}
          />

          <Input
            label="Confirm New Password"
            id="confirmPassword"
            type="password"
            placeholder="••••••••"
            value={confirmPassword}
            disabled={status === 'loading' || status === 'success'}
            onChange={(e) => setConfirmPassword(e.target.value)}
            error={validationErrors.confirmPassword}
          />

          <Button
            type="submit"
            variant="primary"
            disabled={!password || !confirmPassword || status === 'loading' || status === 'success'}
            iconLeft={status === 'loading' && <RefreshCw size={14} className="animate-spin" />}
            style={{ width: '100%' }}
          >
            {status === 'loading' ? 'Saving...' : 'Update Password'}
          </Button>
        </form>
      </Card>
    </div>
  );
};
export default ResetPassword;
