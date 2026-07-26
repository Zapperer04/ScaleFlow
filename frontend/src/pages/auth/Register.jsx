import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import Input from '../../components/ui/Input';
import Button from '../../components/ui/Button';
import Card from '../../components/ui/Card';
import { ScaleFlowLogo } from '../../components/layout/PublicLayout';
import { RefreshCw } from 'lucide-react';

export const Register = () => {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [name, setName] = useState('');
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [agreeTerms, setAgreeTerms] = useState(false);

  const [status, setStatus] = useState('idle');
  const [errorMsg, setErrorMsg] = useState('');
  const [validationErrors, setValidationErrors] = useState({});

  const validate = () => {
    const errs = {};
    if (!name.trim()) errs.name = 'Full Name is required.';
    if (!username.trim()) errs.username = 'Username is required.';
    
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) errs.email = 'Please enter a valid email.';

    if (password.length < 6) errs.password = 'Password must be at least 6 characters.';
    if (password !== confirmPassword) errs.confirmPassword = 'Passwords do not match.';
    if (!agreeTerms) errs.agreeTerms = 'You must accept the terms.';

    setValidationErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e) => {
    e?.preventDefault();
    if (!validate()) return;

    setStatus('loading');
    setErrorMsg('');

    try {
      await register(username, name, email, password);
      setStatus('success');
      setTimeout(() => {
        navigate('/verify-email');
      }, 1000);
    } catch (err) {
      setStatus('failure');
      setErrorMsg(err.message || 'Error occurred during registration.');
    }
  };

  const isFormInvalid = !name || !username || !email || !password || !confirmPassword || !agreeTerms;

  return (
    <div
      style={{
        minHeight: 'calc(100vh - 146px)',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        padding: 'var(--spacing-64) var(--spacing-32)',
        maxWidth: 'var(--max-width-reading)',
        margin: '0 auto',
      }}
    >
      <Card style={{ width: '100%', maxWidth: '460px', padding: 'var(--spacing-32)', boxShadow: 'var(--shadow-lg)' }}>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-16)' }}>
          
          {/* Brand Header */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid var(--border-divider)', paddingBottom: '12px' }}>
            <ScaleFlowLogo size={22} />
            <span style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: '1rem', letterSpacing: 'var(--ls-tight)' }}>ScaleFlow</span>
          </div>

          <div>
            <h2 style={{ fontSize: 'var(--font-size-2xl)', fontFamily: 'var(--font-display)', marginBottom: '8px' }}>Create an account</h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)', margin: 0 }}>
              Create your workspace in under a minute. Start building structured document graphs.
            </p>
          </div>

          {/* Success Notification */}
          {status === 'success' && (
            <div
              style={{
                padding: 'var(--spacing-12)',
                backgroundColor: 'rgba(16, 185, 129, 0.04)',
                border: '1.5px solid var(--color-success)',
                borderRadius: 'var(--radius-6)',
                color: 'var(--color-success)',
                fontSize: 'var(--font-size-xs)',
              }}
            >
              Account created successfully! Redirecting to email verification...
            </div>
          )}

          {/* Failure Alert */}
          {status === 'failure' && (
            <div
              style={{
                padding: 'var(--spacing-12)',
                backgroundColor: 'rgba(244, 63, 94, 0.04)',
                border: '1.5px solid var(--color-failure)',
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
                <RefreshCw size={12} /> Retry Registration
              </button>
            </div>
          )}

          <Input
            label="Full Name"
            id="name"
            placeholder="John Doe"
            value={name}
            disabled={status === 'loading' || status === 'success'}
            onChange={(e) => setName(e.target.value)}
            error={validationErrors.name}
          />

          <Input
            label="Username"
            id="username"
            placeholder="johndoe"
            value={username}
            disabled={status === 'loading' || status === 'success'}
            onChange={(e) => setUsername(e.target.value)}
            error={validationErrors.username}
          />

          <Input
            label="Email Address"
            id="email"
            type="email"
            placeholder="john@example.com"
            value={email}
            disabled={status === 'loading' || status === 'success'}
            onChange={(e) => setEmail(e.target.value)}
            error={validationErrors.email}
          />

          <Input
            label="Password"
            id="password"
            type="password"
            placeholder="••••••••"
            value={password}
            disabled={status === 'loading' || status === 'success'}
            onChange={(e) => setPassword(e.target.value)}
            error={validationErrors.password}
          />

          <Input
            label="Confirm Password"
            id="confirmPassword"
            type="password"
            placeholder="••••••••"
            value={confirmPassword}
            disabled={status === 'loading' || status === 'success'}
            onChange={(e) => setConfirmPassword(e.target.value)}
            error={validationErrors.confirmPassword}
          />

          <label
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '8px',
              fontSize: 'var(--font-size-xs)',
              cursor: 'pointer',
              color: 'var(--text-secondary)',
              marginTop: '8px',
            }}
          >
            <input
              type="checkbox"
              checked={agreeTerms}
              disabled={status === 'loading' || status === 'success'}
              onChange={(e) => setAgreeTerms(e.target.checked)}
              style={{ marginTop: '2px' }}
            />
            <span>
              I agree to the{' '}
              <a href="#terms" style={{ color: 'var(--color-accent)' }}>
                Terms of Service
              </a>{' '}
              and{' '}
              <a href="#privacy" style={{ color: 'var(--color-accent)' }}>
                Privacy Policy
              </a>
            </span>
          </label>
          {validationErrors.agreeTerms && (
            <div style={{ color: 'var(--color-failure)', fontSize: 'var(--font-size-xs)' }}>
              {validationErrors.agreeTerms}
            </div>
          )}

          <Button
            type="submit"
            variant="primary"
            disabled={isFormInvalid || status === 'loading' || status === 'success'}
            iconLeft={status === 'loading' && <RefreshCw size={14} className="animate-spin" />}
            style={{ width: '100%', height: '40px', marginTop: '8px' }}
          >
            {status === 'loading' ? 'Creating account...' : 'Create Account'}
          </Button>

          <div style={{ textAlign: 'center', fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)' }}>
            Already have an account?{' '}
            <a href="/login" style={{ color: 'var(--color-accent)', fontWeight: 500 }}>
              Login
            </a>
          </div>
        </form>
      </Card>
    </div>
  );
};
export default Register;
