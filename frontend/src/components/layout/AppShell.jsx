import React, { useState, useEffect, useCallback } from 'react';
import { Layers, Cpu, RefreshCw, Menu, X, Bell, Search, Info, CheckCircle2, AlertTriangle, AlertOctagon, Trash2 } from 'lucide-react';
import Button from '../ui/Button';
import Breadcrumb from '../ui/Breadcrumb';
import { NAVIGATION_CATEGORIES, getViewDetails } from '../../routes/navigation';
import useMediaQuery from '../../hooks/useMediaQuery';
import { useNotification } from '../../contexts/NotificationContext';
import { globalSearch } from '../../services/search';

/**
 * Reusable layout wrapper for the ScaleFlow application workspace.
 */
export const AppShell = ({
  activeView,
  onNavigateToView,
  redisStatus,
  dbStatus,
  qdrantStatus,
  leaderId,
  workers = [],
  orchestratorCount,
  queueStats = {},
  queuePressure,
  testing = false,
  onRunTests,
  children
}) => {
  const isMobile = useMediaQuery('(max-width: 768px)');
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Overhaul states
  const { notifications, unreadCount, markAsRead, clearAll } = useNotification();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);

  const handleSearchChange = async (e) => {
    const q = e.target.value;
    setSearchQuery(q);
    if (q.trim().length > 1) {
      try {
        const res = await globalSearch(q);
        setSearchResults(res);
      } catch (err) {
        console.error("Global search error", err);
      }
    } else {
      setSearchResults(null);
    }
  };

  const activeWorkersCount = workers.filter(w => w.status !== 'offline').length;
  const viewDetails = getViewDetails(activeView);

  const breadcrumbItems = [
    { label: 'ScaleFlow Workspace', onClick: () => onNavigateToView('workspace') },
    { label: viewDetails.label }
  ];

  const sidebarClass = isMobile && !sidebarOpen ? 'sidebar-collapsed' : '';

  const handleNavigate = (viewId) => {
    onNavigateToView(viewId);
    if (isMobile) {
      setSidebarOpen(false);
    }
  };

  return (
    <div className="app-container">
      
      {/* Mobile Top Navbar with toggles */}
      {isMobile && (
        <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-panel)', padding: 'var(--spacing-12) var(--spacing-16)', borderBottom: '1px solid var(--border-subtle)', zIndex: 100 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-8)' }}>
            <Layers size={18} style={{ color: 'var(--color-accent)' }} />
            <span className="text-body" style={{ fontWeight: 'var(--font-weight-heavy)' }}>ScaleFlow</span>
          </div>
          <button 
            onClick={() => setSidebarOpen(prev => !prev)}
            style={{ background: 'none', border: 'none', color: 'var(--text-primary)', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
            aria-label="Toggle sidebar menu"
          >
            {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </header>
      )}

      {/* 1. LEFT SIDEBAR */}
      <aside className={`sidebar ${sidebarClass}`.trim()} role="navigation" aria-label="Sidebar Navigation">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-32)' }}>
          {!isMobile && (
            <div className="sidebar-branding">
              <div className="sidebar-logo">
                <Layers size={22} style={{ color: 'var(--color-accent)' }} />
                <span className="text-h3" style={{ fontWeight: 'var(--font-weight-heavy)' }}>ScaleFlow</span>
              </div>
              <span className="sidebar-subtitle text-caption">Distributed Platform</span>
            </div>
          )}

          <nav className="sidebar-nav">
            {NAVIGATION_CATEGORIES.map(category => (
              <React.Fragment key={category.id}>
                <div 
                  className="text-caption" 
                  style={{ 
                    color: 'var(--text-disabled)', 
                    fontWeight: 'var(--font-weight-bold)', 
                    textTransform: 'uppercase', 
                    letterSpacing: 'var(--ls-wide)', 
                    marginTop: category.id === 'tools' ? 'var(--spacing-24)' : '0', 
                    marginBottom: 'var(--spacing-8)', 
                    paddingLeft: 'var(--spacing-8)' 
                  }}
                >
                  {category.label}
                </div>
                {category.items.map(item => {
                  const Icon = item.icon;
                  return (
                    <button 
                      key={item.id}
                      className={`sidebar-nav-item ${activeView === item.id ? 'active' : ''}`}
                      onClick={() => handleNavigate(item.id)}
                    >
                      <Icon size={18} />
                      {item.label}
                    </button>
                  );
                })}
              </React.Fragment>
            ))}
          </nav>
        </div>

        {/* Cluster Infrastructure Status Footer */}
        <div className="sidebar-footer">
          <div className="cluster-status-title text-caption" style={{ fontWeight: 'var(--font-weight-bold)' }}>Infrastructure Health</div>
          <div className="cluster-status-list">
            <div className="cluster-status-item">
              <span>Redis Broker</span>
              <div className="status-dot-container">
                <span className={`status-dot ${redisStatus}`} />
                <span className="text-small">{redisStatus === 'online' ? 'Connected' : 'Offline'}</span>
              </div>
            </div>
            
            <div className="cluster-status-item">
              <span>Postgres DB</span>
              <div className="status-dot-container">
                <span className={`status-dot ${dbStatus}`} />
                <span className="text-small">{dbStatus === 'online' ? 'Connected' : 'Offline'}</span>
              </div>
            </div>

            <div className="cluster-status-item">
              <span>Qdrant Store</span>
              <div className="status-dot-container">
                <span className={`status-dot ${qdrantStatus}`} />
                <span className="text-small">{qdrantStatus === 'online' ? 'Connected' : 'Offline'}</span>
              </div>
            </div>

            <div className="cluster-status-item" style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: 'var(--spacing-8)', marginTop: 'var(--spacing-4)' }}>
              <span>HA Status</span>
              <span className="text-small" style={{ fontWeight: 'var(--font-weight-bold)', color: 'var(--text-primary)' }}>
                {leaderId !== 'Checking...' && leaderId !== 'None' ? 'Leader' : 'Replica'}
              </span>
            </div>

            <div className="cluster-status-item">
              <span>Online Nodes</span>
              <span className="text-small" style={{ fontWeight: 'var(--font-weight-bold)', color: 'var(--color-accent)' }}>
                {activeWorkersCount} Workers
              </span>
            </div>
          </div>
        </div>
      </aside>

      {/* 2. MAIN VIEWPORT */}
      <main className="main-viewport" role="main">
        
        {/* Top Control Bar */}
        <header className="top-bar" role="banner" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', height: '60px', borderBottom: '1px solid var(--border-subtle)', padding: '0 var(--spacing-24)', background: 'var(--bg-panel)' }}>
          <div className="top-bar-left" style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-16)' }}>
            <Breadcrumb items={breadcrumbItems} />
            
            <span className={`mode-badge text-caption ${queuePressure > 60 ? 'backpressure' : queuePressure > 30 ? 'high-load' : ''}`}>
              {queuePressure > 60 ? 'Queue Backpressure: Active' : queuePressure > 30 ? 'Load Mode: High' : 'Load Mode: Optimal'}
            </span>
          </div>

          <div className="top-bar-right" style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-20)' }}>
            <div className="top-bar-stats text-caption hide-mobile" style={{ display: 'flex', gap: 'var(--spacing-16)', color: 'var(--text-secondary)' }}>
              <div>
                <span>Orchestrators: </span>
                <span className="top-bar-stat-val" style={{ color: 'var(--text-primary)', fontWeight: 'var(--font-weight-bold)' }}>{orchestratorCount}</span>
              </div>
              <div style={{ borderLeft: '1px solid var(--border-subtle)', paddingLeft: 'var(--spacing-12)' }}>
                <span>Active Leader ID: </span>
                <span className="top-bar-stat-val" style={{ fontFamily: 'var(--font-family-mono)', color: 'var(--text-primary)' }}>
                  {leaderId.length > 10 ? `${leaderId.slice(0, 8)}...` : leaderId}
                </span>
              </div>
              <div style={{ borderLeft: '1px solid var(--border-subtle)', paddingLeft: 'var(--spacing-12)' }}>
                <span>Queue Size: </span>
                <span className="top-bar-stat-val" style={{ color: queuePressure > 60 ? 'var(--color-failure)' : 'var(--text-primary)', fontWeight: 'var(--font-weight-bold)' }}>
                  {queueStats.total || 0}
                </span>
              </div>
            </div>

            {/* Global Search Trigger */}
            <button 
              onClick={() => setSearchOpen(true)}
              style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', padding: '8px' }}
              aria-label="Open global search"
            >
              <Search size={18} />
            </button>

            {/* Notification Bell */}
            <div style={{ position: 'relative' }}>
              <button 
                onClick={() => setDrawerOpen(true)}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', padding: '8px' }}
                aria-label="Open notifications"
              >
                <Bell size={18} />
                {unreadCount > 0 && (
                  <span style={{
                    position: 'absolute',
                    top: '2px',
                    right: '2px',
                    background: 'var(--color-accent)',
                    color: '#fff',
                    borderRadius: '50%',
                    width: '16px',
                    height: '16px',
                    fontSize: '0.65rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontWeight: 'bold'
                  }}>
                    {unreadCount}
                  </span>
                )}
              </button>
            </div>

            <Button 
              variant="primary" 
              onClick={onRunTests}
              disabled={testing}
              iconLeft={testing ? <RefreshCw size={14} className="animate-spin" /> : <Cpu size={14} />}
            >
              Run System Tests
            </Button>
          </div>
        </header>

        {/* Dynamic Inner Children Workspace Pages */}
        <div className="workspace-content" style={{ padding: 'var(--spacing-24)', flex: 1, overflowY: 'auto' }}>
          {children}
        </div>
      </main>

      {/* Notification History Drawer */}
      {drawerOpen && (
        <div style={{
          position: 'fixed',
          top: 0,
          right: 0,
          width: '380px',
          height: '100%',
          background: 'var(--bg-panel)',
          boxShadow: '-4px 0 24px rgba(0,0,0,0.4)',
          borderLeft: '1px solid var(--border-subtle)',
          zIndex: 1000,
          display: 'flex',
          flexDirection: 'column'
        }}>
          <div style={{ padding: '20px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700 }}>Notifications</h3>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <button onClick={clearAll} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Trash2 size={12} /> Clear all
              </button>
              <button onClick={() => setDrawerOpen(false)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
                <X size={18} />
              </button>
            </div>
          </div>

          <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {notifications.map(notif => {
              const Icon = notif.severity === 'success' ? CheckCircle2 : notif.severity === 'error' ? AlertOctagon : notif.severity === 'warning' ? AlertTriangle : Info;
              const color = notif.severity === 'success' ? 'var(--color-success)' : notif.severity === 'error' ? 'var(--color-failure)' : notif.severity === 'warning' ? 'var(--color-warning)' : 'var(--color-accent)';
              
              return (
                <div 
                  key={notif.id}
                  onClick={() => markAsRead(notif.id)}
                  style={{
                    background: notif.status === 'unread' ? 'rgba(255,255,255,0.03)' : 'transparent',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '8px',
                    padding: '12px',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    position: 'relative',
                    borderLeft: `3px solid ${color}`
                  }}
                >
                  <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
                    <Icon size={16} style={{ color, marginTop: '2px', flexShrink: 0 }} />
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600, fontSize: '0.8rem' }}>{notif.title}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>{notif.message}</div>
                      <div style={{ fontSize: '0.65rem', color: 'var(--text-disabled)', marginTop: '6px' }}>
                        {new Date(notif.created_at || notif.timestamp).toLocaleTimeString()}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
            {notifications.length === 0 && (
              <div style={{ textAlign: 'center', color: 'var(--text-disabled)', padding: '40px', fontSize: '0.8rem' }}>
                No active notifications.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Global Search Modal */}
      {searchOpen && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          background: 'rgba(0,0,0,0.6)',
          backdropFilter: 'blur(4px)',
          zIndex: 1000,
          display: 'flex',
          justifyContent: 'center',
          paddingTop: '80px'
        }} onClick={() => setSearchOpen(false)}>
          <div style={{
            width: '600px',
            maxHeight: '450px',
            background: 'var(--bg-panel)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '12px',
            boxShadow: '0 12px 48px rgba(0,0,0,0.5)',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden'
          }} onClick={e => e.stopPropagation()}>
            <div style={{ padding: '16px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', gap: '12px', alignItems: 'center' }}>
              <Search size={18} style={{ color: 'var(--text-muted)' }} />
              <input 
                type="text"
                autoFocus
                placeholder="Search documents, entities, logs, pipelines..."
                value={searchQuery}
                onChange={handleSearchChange}
                style={{
                  flex: 1,
                  background: 'none',
                  border: 'none',
                  outline: 'none',
                  color: 'var(--text-primary)',
                  fontSize: '0.9rem'
                }}
              />
              <button onClick={() => setSearchOpen(false)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>✕</button>
            </div>

            <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {searchResults && Object.keys(searchResults).map(category => {
                const items = searchResults[category] || [];
                if (items.length === 0) return null;
                return (
                  <div key={category}>
                    <div style={{ fontSize: '0.7rem', fontWeight: 'bold', color: 'var(--text-disabled)', textTransform: 'uppercase', marginBottom: '8px' }}>{category}</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      {items.map(item => (
                        <button
                          key={item.id}
                          onClick={() => {
                            setSearchOpen(false);
                            if (category === 'documents') {
                              onNavigateToView('documents');
                            } else if (category === 'pipelines') {
                              onNavigateToView('pipelines');
                            }
                          }}
                          style={{
                            background: 'rgba(255,255,255,0.01)',
                            border: '1px solid var(--border-subtle)',
                            borderRadius: '6px',
                            padding: '8px 12px',
                            textAlign: 'left',
                            color: 'var(--text-primary)',
                            cursor: 'pointer',
                            fontSize: '0.8rem',
                            display: 'block',
                            width: '100%',
                            transition: 'background 0.2s'
                          }}
                        >
                          {item.filename || item.name || item.detail || item.title}
                        </button>
                      ))}
                    </div>
                  </div>
                );
              })}
              {!searchResults && searchQuery.trim().length > 1 && (
                <div style={{ textAlign: 'center', color: 'var(--text-disabled)', padding: '20px', fontSize: '0.8rem' }}>No results found.</div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
export default AppShell;
