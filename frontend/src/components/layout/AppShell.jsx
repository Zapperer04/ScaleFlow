import React, { useState } from 'react';
import { Layers, Cpu, RefreshCw, Menu, X } from 'lucide-react';
import Button from '../ui/Button';
import Breadcrumb from '../ui/Breadcrumb';
import { NAVIGATION_CATEGORIES, getViewDetails } from '../../routes/navigation';
import useMediaQuery from '../../hooks/useMediaQuery';

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

  const activeWorkersCount = workers.filter(w => w.status !== 'offline').length;
  const viewDetails = getViewDetails(activeView);

  const breadcrumbItems = [
    { label: 'ScaleFlow Workspace', onClick: () => onNavigateToView('overview') },
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
    </div>
  );
};
export default AppShell;
