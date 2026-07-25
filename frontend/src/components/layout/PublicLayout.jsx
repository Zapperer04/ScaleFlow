import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { Menu, X, Sun, Moon, Github } from 'lucide-react';
import Button from '../ui/Button';

export const ScaleFlowLogo = ({ size = 26 }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 32 32"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    style={{ transition: 'transform var(--transition-normal)' }}
  >
    {/* Background outline representing a document block */}
    <rect x="3" y="3" width="26" height="26" rx="6" stroke="var(--border-subtle)" strokeWidth="1.5" />
    
    {/* Flowing document lines */}
    <path
      d="M8 8H20M8 13H15"
      stroke="var(--text-secondary)"
      strokeWidth="2"
      strokeLinecap="round"
    />
    
    {/* Nodes representing the knowledge graph mapping */}
    <circle cx="23" cy="14" r="3" fill="var(--color-accent)" />
    <circle cx="18" cy="22" r="3" fill="var(--color-success)" />
    <circle cx="10" cy="21" r="2.5" fill="var(--text-muted)" />
    
    {/* Connection paths */}
    <path
      d="M21.5 16.5L19.5 19.5M16 22H12"
      stroke="var(--color-accent)"
      strokeWidth="1.2"
      strokeDasharray="2 2"
    />
  </svg>
);

export const PublicLayout = ({ children }) => {
  const { token, logout } = useAuth();
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('sf_theme') || 'theme-dark';
  });
  const [showDocsPopup, setShowDocsPopup] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    document.documentElement.className = theme;
    localStorage.setItem('sf_theme', theme);
  }, [theme]);

  useEffect(() => {
    document.body.style.overflow = 'auto';
    return () => {
      document.body.style.overflow = 'hidden';
    };
  }, []);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'theme-light' ? 'theme-dark' : 'theme-light'));
  };

  const handleDocsClick = (e) => {
    e.preventDefault();
    setShowDocsPopup(true);
    setTimeout(() => {
      setShowDocsPopup(false);
    }, 2000);
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        minHeight: '100vh',
        backgroundColor: 'var(--bg-primary)',
        color: 'var(--text-primary)',
        fontFamily: 'var(--font-body)',
      }}
    >
      {/* Sticky Premium Header */}
      <header
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 100,
          transition: 'all var(--transition-normal)',
          backgroundColor: scrolled ? 'rgba(11, 15, 25, 0.85)' : 'transparent',
          backdropFilter: scrolled ? 'blur(16px)' : 'none',
          borderBottom: scrolled ? '1px solid var(--border-subtle)' : '1px solid transparent',
        }}
      >
        <div
          style={{
            maxWidth: 'var(--max-width-landing)',
            margin: '0 auto',
            padding: '0 var(--spacing-32)',
            height: '76px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          {/* Left Brand Identity */}
          <a
            href="/"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--spacing-12)',
              fontSize: '1.15rem',
              fontWeight: 'var(--font-weight-semibold)',
              letterSpacing: 'var(--ls-tight)',
              color: 'var(--text-primary)',
            }}
          >
            <ScaleFlowLogo />
            <span style={{ fontFamily: 'var(--font-display)', fontWeight: 700 }}>ScaleFlow</span>
          </a>

          {/* Middle Nav - Increased spacing and better font visual weights */}
          <nav
            style={{
              display: 'none',
              gap: 'var(--spacing-32)',
              alignItems: 'center',
            }}
            className="desktop-nav"
          >
            <a href="/#hero" style={{ fontSize: 'var(--font-size-sm)', fontWeight: 500, color: 'var(--text-secondary)' }}>Home</a>
            <a href="/#features" style={{ fontSize: 'var(--font-size-sm)', fontWeight: 500, color: 'var(--text-secondary)' }}>Features</a>
            <a href="/#how-it-works" style={{ fontSize: 'var(--font-size-sm)', fontWeight: 500, color: 'var(--text-secondary)' }}>How it Works</a>
            <a
              href="#docs"
              onClick={handleDocsClick}
              style={{
                fontSize: 'var(--font-size-sm)',
                fontWeight: 500,
                color: 'var(--text-secondary)',
                position: 'relative',
              }}
            >
              Docs
              {showDocsPopup && (
                <span
                  style={{
                    position: 'absolute',
                    top: '28px',
                    left: '50%',
                    transform: 'translateX(-50%)',
                    backgroundColor: 'var(--bg-panel)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-6)',
                    padding: 'var(--spacing-4) var(--spacing-8)',
                    fontSize: 'var(--font-size-xs)',
                    color: 'var(--color-success)',
                    whiteSpace: 'nowrap',
                    boxShadow: 'var(--shadow-md)',
                    zIndex: 200,
                  }}
                >
                  Coming Soon
                </span>
              )}
            </a>
            <a
              href="https://github.com/Zapperer04/Task-Schedular"
              target="_blank"
              rel="noreferrer"
              style={{
                display: 'flex',
                alignItems: 'center',
                color: 'var(--text-secondary)',
                transition: 'color var(--transition-normal)',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-primary)')}
              onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-secondary)')}
              aria-label="Source code"
            >
              <Github size={16} />
            </a>
          </nav>

          {/* Right Actions - Beautiful, clean alignment */}
          <div
            style={{
              display: 'none',
              gap: 'var(--spacing-16)',
              alignItems: 'center',
            }}
            className="desktop-nav"
          >
            {/* Theme Toggle in visual layout */}
            <button
              onClick={toggleTheme}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--text-secondary)',
                cursor: 'pointer',
                padding: 'var(--spacing-8)',
                display: 'flex',
                alignItems: 'center',
                transition: 'color var(--transition-normal)',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-primary)')}
              onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-secondary)')}
              aria-label="Toggle theme"
            >
              {theme === 'theme-light' ? <Moon size={16} /> : <Sun size={16} />}
            </button>
            
            {token ? (
              <>
                <Button variant="secondary" onClick={() => (window.location.href = '/workspace')}>
                  Workspace
                </Button>
                <Button variant="ghost" onClick={logout}>
                  Logout
                </Button>
              </>
            ) : (
              <>
                <Button variant="ghost" style={{ fontSize: 'var(--font-size-sm)' }} onClick={() => (window.location.href = '/login')}>
                  Login
                </Button>
                <Button variant="primary" style={{ height: '36px', fontSize: 'var(--font-size-sm)', padding: '0 var(--spacing-16)' }} onClick={() => (window.location.href = '/register')}>
                  Get Started
                </Button>
              </>
            )}
          </div>

          {/* Mobile Menu Action */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--spacing-12)',
            }}
            className="mobile-nav-toggle"
          >
            <button
              onClick={toggleTheme}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--text-secondary)',
                cursor: 'pointer',
                padding: 'var(--spacing-8)',
                display: 'flex',
                alignItems: 'center',
              }}
              aria-label="Toggle theme"
            >
              {theme === 'theme-light' ? <Moon size={18} /> : <Sun size={18} />}
            </button>
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--text-primary)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
              }}
              aria-label="Toggle Menu"
            >
              {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>
        </div>

        {/* Mobile Menu Drawer */}
        {mobileMenuOpen && (
          <div
            style={{
              position: 'fixed',
              top: '76px',
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: 'var(--bg-primary)',
              zIndex: 99,
              padding: 'var(--spacing-32)',
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--spacing-24)',
              borderTop: '1px solid var(--border-subtle)',
            }}
          >
            <a
              href="/#hero"
              onClick={() => setMobileMenuOpen(false)}
              style={{ fontSize: 'var(--font-size-lg)', fontWeight: 500 }}
            >
              Home
            </a>
            <a
              href="/#features"
              onClick={() => setMobileMenuOpen(false)}
              style={{ fontSize: 'var(--font-size-lg)', fontWeight: 500 }}
            >
              Features
            </a>
            <a
              href="/#how-it-works"
              onClick={() => setMobileMenuOpen(false)}
              style={{ fontSize: 'var(--font-size-lg)', fontWeight: 500 }}
            >
              How it Works
            </a>
            <a
              href="#docs"
              onClick={(e) => {
                handleDocsClick(e);
                setMobileMenuOpen(false);
              }}
              style={{ fontSize: 'var(--font-size-lg)', fontWeight: 500 }}
            >
              Docs
            </a>
            <a
              href="https://github.com/Zapperer04/Task-Schedular"
              target="_blank"
              rel="noreferrer"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                fontSize: 'var(--font-size-lg)',
                fontWeight: 500,
              }}
            >
              <Github size={18} /> GitHub Source
            </a>
            <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: 'var(--spacing-24)', marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {token ? (
                <>
                  <Button variant="primary" onClick={() => (window.location.href = '/workspace')}>
                    Go to Workspace
                  </Button>
                  <Button variant="secondary" onClick={logout}>
                    Logout
                  </Button>
                </>
              ) : (
                <>
                  <Button variant="secondary" onClick={() => (window.location.href = '/login')}>
                    Login
                  </Button>
                  <Button variant="primary" onClick={() => (window.location.href = '/register')}>
                    Get Started
                  </Button>
                </>
              )}
            </div>
          </div>
        )}
      </header>

      {/* Main Content Area */}
      <main style={{ flex: 1 }}>{children}</main>

      {/* Production-Grade Footer */}
      <footer
        style={{
          borderTop: '1px solid var(--border-subtle)',
          backgroundColor: 'rgba(0, 0, 0, 0.15)',
          padding: 'var(--spacing-64) 0 var(--spacing-32) 0',
        }}
      >
        <div
          style={{
            maxWidth: 'var(--max-width-landing)',
            margin: '0 auto',
            padding: '0 var(--spacing-32)',
          }}
        >
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
              gap: 'var(--spacing-48)',
              marginBottom: 'var(--spacing-64)',
            }}
          >
            {/* Identity & Mission */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-16)', gridColumn: 'span 2' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-8)' }}>
                <ScaleFlowLogo size={22} />
                <span style={{ fontWeight: 'var(--font-weight-bold)', fontFamily: 'var(--font-display)' }}>ScaleFlow</span>
              </div>
              <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-xs)', lineHeight: 'var(--lh-relaxed)', maxWidth: '280px' }}>
                Intelligent Document Understanding powered by layout-aware hybrid Graph RAG.
              </p>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
                <span style={{ display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'var(--color-success)' }} />
                <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', fontWeight: 500 }}>All Systems Operational</span>
              </div>
            </div>

            {/* Product Column */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-12)' }}>
              <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-bold)', color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Product
              </span>
              <a href="/#features" style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)' }}>Features</a>
              <a href="/#how-it-works" style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)' }}>How it Works</a>
              <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', cursor: 'default' }}>Roadmap (Coming Soon)</span>
            </div>

            {/* Resources Column */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-12)' }}>
              <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-bold)', color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Resources
              </span>
              <a href="#docs" onClick={handleDocsClick} style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)' }}>Docs (Coming Soon)</a>
              <a href="https://github.com/Zapperer04/Task-Schedular" target="_blank" rel="noreferrer" style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)' }}>GitHub Source</a>
              <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', cursor: 'default' }}>API Reference (Coming Soon)</span>
              <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', cursor: 'default' }}>Research (Coming Soon)</span>
            </div>

            {/* Legal Column */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-12)' }}>
              <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-bold)', color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Legal
              </span>
              <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', cursor: 'default' }}>Privacy (Coming Soon)</span>
              <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', cursor: 'default' }}>Terms (Coming Soon)</span>
              <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', cursor: 'default' }}>License (Coming Soon)</span>
              <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', cursor: 'default' }}>Contact (Coming Soon)</span>
            </div>
          </div>

          {/* Bottom copyright & details */}
          <div
            style={{
              borderTop: '1px solid var(--border-divider)',
              paddingTop: 'var(--spacing-24)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: 'var(--spacing-16)',
            }}
          >
            <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
              &copy; {new Date().getFullYear()} ScaleFlow. Built for high-reliability data infrastructure.
            </span>
            <div style={{ display: 'flex', gap: '16px' }}>
              <a href="https://github.com/Zapperer04/Task-Schedular" target="_blank" rel="noreferrer" style={{ color: 'var(--text-muted)', transition: 'color var(--transition-normal)' }}>
                <Github size={16} />
              </a>
            </div>
          </div>
        </div>
      </footer>

      {/* Media query styling overrides directly injected */}
      <style>{`
        @media (min-width: 769px) {
          .desktop-nav {
            display: flex !important;
          }
          .mobile-nav-toggle {
            display: none !important;
          }
        }
      `}</style>
    </div>
  );
};
export default PublicLayout;
