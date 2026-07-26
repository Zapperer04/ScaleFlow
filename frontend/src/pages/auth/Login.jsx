import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import Input from '../../components/ui/Input';
import Button from '../../components/ui/Button';
import Card from '../../components/ui/Card';
import { ScaleFlowLogo } from '../../components/layout/PublicLayout';
import { RefreshCw, Github } from 'lucide-react';

export const Login = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);

  const [status, setStatus] = useState('idle');
  const [errorMsg, setErrorMsg] = useState('');
  const [validationErrors, setValidationErrors] = useState({});

  // Interactive SVG state
  const [hoveredNode, setHoveredNode] = useState(null);

  const validate = () => {
    const errs = {};
    if (!username.trim()) errs.username = 'Username is required.';
    if (!password) errs.password = 'Password is required.';
    setValidationErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e) => {
    e?.preventDefault();
    if (!validate()) return;

    setStatus('loading');
    setErrorMsg('');
    
    try {
      await login(username, password, rememberMe);
      setStatus('success');
      setTimeout(() => {
        navigate('/workspace');
      }, 700);
    } catch (err) {
      setStatus('failure');
      setErrorMsg(err.message || 'Network error, please try again.');
    }
  };

  const isFormInvalid = !username.trim() || !password;

  return (
    <div
      style={{
        minHeight: 'calc(100vh - 146px)',
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))',
        maxWidth: 'var(--max-width-landing)',
        margin: '0 auto',
        padding: 'var(--spacing-64) var(--spacing-32)',
        alignItems: 'center',
        gap: 'var(--spacing-64)',
      }}
    >
      {/* Left side Login Form */}
      <div style={{ display: 'flex', justifyContent: 'center' }}>
        <Card style={{ width: '100%', maxWidth: '460px', padding: 'var(--spacing-32)', boxShadow: 'var(--shadow-lg)' }}>
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-20)' }}>
            
            {/* Brand Header */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid var(--border-divider)', paddingBottom: '12px' }}>
              <ScaleFlowLogo size={22} />
              <span style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: '1rem', letterSpacing: 'var(--ls-tight)' }}>ScaleFlow</span>
            </div>

            <div>
              <h2 style={{ fontSize: 'var(--font-size-2xl)', fontFamily: 'var(--font-display)', marginBottom: '8px' }}>Welcome back</h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)', margin: 0 }}>
                Enter your credentials to access the ScaleFlow platform.
              </p>
            </div>

            {/* Error Message & Retry */}
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
                  <RefreshCw size={12} /> Retry Connection
                </button>
              </div>
            )}

            {/* Success State */}
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
                Login successful. Redirecting to workspace...
              </div>
            )}

            <Input
              label="Username"
              id="username"
              type="text"
              placeholder="e.g. admin, manager, user"
              value={username}
              disabled={status === 'loading' || status === 'success'}
              onChange={(e) => setUsername(e.target.value)}
              error={validationErrors.username}
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

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 'var(--font-size-xs)' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', color: 'var(--text-secondary)' }}>
                <input
                  type="checkbox"
                  checked={rememberMe}
                  disabled={status === 'loading' || status === 'success'}
                  onChange={(e) => setRememberMe(e.target.checked)}
                />
                Remember me
              </label>
              <a href="/forgot-password" style={{ color: 'var(--color-accent)', fontWeight: 500 }}>
                Forgot Password?
              </a>
            </div>

            <Button
              type="submit"
              variant="primary"
              disabled={isFormInvalid || status === 'loading' || status === 'success'}
              iconLeft={status === 'loading' && <RefreshCw size={14} className="animate-spin" />}
              style={{ width: '100%', height: '40px' }}
            >
              {status === 'loading' ? 'Authenticating...' : 'Continue'}
            </Button>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-disabled)', fontSize: '10px', fontWeight: 600 }}>
              <span style={{ flex: 1, height: '1px', backgroundColor: 'var(--border-subtle)' }} />
              <span>OR CONTINUE WITH</span>
              <span style={{ flex: 1, height: '1px', backgroundColor: 'var(--border-subtle)' }} />
            </div>

            <div style={{ display: 'flex', gap: '12px' }}>
              <Button type="button" variant="secondary" style={{ flex: 1, height: '36px' }} onClick={() => {}} disabled>
                Google
              </Button>
              <Button type="button" variant="secondary" style={{ flex: 1, height: '36px', gap: '6px' }} onClick={() => {}} disabled>
                <Github size={14} /> GitHub
              </Button>
            </div>

            <div style={{ textAlign: 'center', fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)' }}>
              Don't have an account?{' '}
              <a href="/register" style={{ color: 'var(--color-accent)', fontWeight: 500 }}>
                Register
              </a>
            </div>
          </form>
        </Card>
      </div>

      {/* Right side SVG illustration (Interactive & Animated) */}
      <div
        className="hide-mobile"
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
        }}
      >
        <svg viewBox="0 0 400 400" width="100%" maxWidth="460px" height="auto" style={{ opacity: 0.95 }}>
          {/* Grid backing */}
          <path d="M 50 0 L 50 400 M 150 0 L 150 400 M 250 0 L 250 400 M 350 0 L 350 400" stroke="rgba(255,255,255,0.015)" strokeWidth="1" />
          <path d="M 0 50 L 400 50 M 0 150 L 400 150 M 0 250 L 400 250 M 0 350 L 400 350" stroke="rgba(255,255,255,0.015)" strokeWidth="1" />

          {/* Connections */}
          <line
            className="pulse-edge"
            x1="200" y1="200" x2="100" y2="140"
            stroke={hoveredNode === 'node1' ? 'var(--color-accent)' : status === 'success' ? 'var(--color-success)' : 'var(--border-subtle)'}
            strokeWidth={hoveredNode === 'node1' ? '3.5' : '2.5'}
            style={{ transition: 'stroke-width 0.15s, stroke 0.15s' }}
          />
          <line
            className="pulse-edge"
            x1="200" y1="200" x2="300" y2="120"
            stroke={hoveredNode === 'node2' ? 'var(--color-accent)' : status === 'success' ? 'var(--color-success)' : 'var(--border-subtle)'}
            strokeWidth={hoveredNode === 'node2' ? '3.5' : '2.5'}
            style={{ transition: 'stroke-width 0.15s, stroke 0.15s' }}
          />
          <line
            className="pulse-edge"
            x1="200" y1="200" x2="290" y2="290"
            stroke={hoveredNode === 'node3' ? 'var(--color-accent)' : status === 'success' ? 'var(--color-success)' : 'var(--color-accent)'}
            strokeWidth={hoveredNode === 'node3' ? '3.5' : '2.5'}
            style={{ transition: 'stroke-width 0.15s, stroke 0.15s' }}
          />
          <line
            className="pulse-edge"
            x1="200" y1="200" x2="110" y2="270"
            stroke={hoveredNode === 'node4' ? 'var(--color-accent)' : status === 'success' ? 'var(--color-success)' : 'var(--border-subtle)'}
            strokeWidth={hoveredNode === 'node4' ? '3.5' : '2.5'}
            style={{ transition: 'stroke-width 0.15s, stroke 0.15s' }}
          />

          {/* Central main network hub */}
          <circle className="hub-center" cx="200" cy="200" r={status === 'success' ? '18' : '14'} fill={status === 'success' ? 'var(--color-success)' : 'var(--color-accent)'} style={{ transition: 'r 0.2s' }} />
          <circle className="rotate-ring-fast" cx="200" cy="200" r="36" stroke="var(--color-accent)" strokeWidth="1.5" strokeDasharray="6 6" fill="none" />

          {/* Sub nodes (Interactive hover boundaries) */}
          <circle
            className="pulse-node"
            cx="100" cy="140" r={hoveredNode === 'node1' ? '13' : '10'}
            fill={hoveredNode === 'node1' ? 'var(--color-accent)' : status === 'success' ? 'var(--color-success)' : 'var(--text-secondary)'}
            style={{ cursor: 'pointer', transition: 'r 0.15s, fill 0.15s' }}
            onMouseEnter={() => setHoveredNode('node1')}
            onMouseLeave={() => setHoveredNode(null)}
          />
          <circle
            className="pulse-node"
            cx="300" cy="120" r={hoveredNode === 'node2' ? '13' : '10'}
            fill={hoveredNode === 'node2' ? 'var(--color-accent)' : status === 'success' ? 'var(--color-success)' : 'var(--text-secondary)'}
            style={{ cursor: 'pointer', transition: 'r 0.15s, fill 0.15s' }}
            onMouseEnter={() => setHoveredNode('node2')}
            onMouseLeave={() => setHoveredNode(null)}
          />
          <circle
            className="pulse-node"
            cx="290" cy="290" r={hoveredNode === 'node3' ? '13' : '10'}
            fill={hoveredNode === 'node3' ? 'var(--color-accent)' : 'var(--color-success)'}
            style={{ cursor: 'pointer', transition: 'r 0.15s, fill 0.15s' }}
            onMouseEnter={() => setHoveredNode('node3')}
            onMouseLeave={() => setHoveredNode(null)}
          />
          <circle
            className="pulse-node"
            cx="110" cy="270" r={hoveredNode === 'node4' ? '13' : '10'}
            fill={hoveredNode === 'node4' ? 'var(--color-accent)' : status === 'success' ? 'var(--color-success)' : 'var(--text-secondary)'}
            style={{ cursor: 'pointer', transition: 'r 0.15s, fill 0.15s' }}
            onMouseEnter={() => setHoveredNode('node4')}
            onMouseLeave={() => setHoveredNode(null)}
          />

          <path d="M 100 140 L 300 120 L 290 290" stroke="rgba(79, 70, 229, 0.25)" strokeWidth="1.5" fill="none" />

          {/* Outer Ring */}
          <circle className="rotate-ring-slow" cx="200" cy="200" r="180" stroke="rgba(255,255,255,0.02)" strokeWidth="2" strokeDasharray="10 20" fill="none" />
        </svg>
      </div>

      {/* CSS Styles Overrides */}
      <style>{`
        @keyframes rotate-ring-clockwise {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes rotate-ring-counter {
          from { transform: rotate(360deg); }
          to { transform: rotate(0deg); }
        }
        @keyframes pulse-node-glow {
          0%, 100% { transform: scale(1); filter: drop-shadow(0 0 2px rgba(79, 70, 229, 0.1)); }
          50% { transform: scale(1.05); filter: drop-shadow(0 0 6px var(--color-accent)); }
        }
        @keyframes edge-glow {
          0%, 100% { opacity: 0.5; }
          50% { opacity: 0.8; }
        }
        @keyframes hub-pulse {
          0%, 100% { filter: drop-shadow(0 0 4px var(--color-accent)); }
          50% { filter: drop-shadow(0 0 10px var(--color-accent)); }
        }
        .rotate-ring-fast {
          transform-origin: 200px 200px;
          animation: rotate-ring-clockwise 20s linear infinite;
        }
        .rotate-ring-slow {
          transform-origin: 200px 200px;
          animation: rotate-ring-counter 60s linear infinite;
        }
        .pulse-node {
          transform-origin: center;
          animation: pulse-node-glow 3.5s ease-in-out infinite;
        }
        .pulse-edge {
          animation: edge-glow 3.5s ease-in-out infinite;
        }
        .hub-center {
          animation: hub-pulse 2.5s ease-in-out infinite;
        }
        @media (max-width: 768px) {
          .hide-mobile {
            display: none !important;
          }
        }

        /* Reduced Motion media query */
        @media (prefers-reduced-motion: reduce) {
          .rotate-ring-fast,
          .rotate-ring-slow,
          .pulse-node,
          .pulse-edge,
          .hub-center {
            animation: none !important;
            transition: none !important;
            transform: none !important;
          }
        }
      `}</style>
    </div>
  );
};
export default Login;
