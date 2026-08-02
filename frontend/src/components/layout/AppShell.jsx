import React, { useState, useEffect } from 'react';
import { 
  Layers, Cpu, Menu, X, Search, Eye,
  Home, UploadCloud, Files, MessageSquare, Activity, 
  ChevronDown, ChevronRight, Database, Settings, Terminal, LineChart,
  ChevronLeft, Layout, Trash2, CheckCircle2, AlertOctagon, AlertTriangle, Info
} from 'lucide-react';
import useMediaQuery from '../../hooks/useMediaQuery';
import { useNotification } from '../../contexts/NotificationContext';
import { usePipeline } from '../../contexts/PipelineContext';
import { useDocument } from '../../contexts/DocumentContext';
import { fetchPipelineDetails } from '../../services/pipelines';
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
  // Dev panel state is lifted to App.js so WorkspaceHome BottomDrawer
  // and this header button share a single source of truth
  devPanelOpen = false,
  onToggleDevPanel,
  children
}) => {
  const isMobile = useMediaQuery('(max-width: 768px)');
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Desktop sidebar collapsed state
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    return localStorage.getItem('scaleflow_sidebar_collapsed') === 'true';
  });

  const toggleSidebarCollapse = () => {
    const nextCollapsed = !sidebarCollapsed;
    setSidebarCollapsed(nextCollapsed);
    localStorage.setItem('scaleflow_sidebar_collapsed', String(nextCollapsed));
  };

  // Dev mode toggle (disabled by default)
  const [devMode, setDevMode] = useState(() => {
    return localStorage.getItem('scaleflow_dev_mode') === 'true';
  });

  const toggleDevMode = () => {
    const newMode = !devMode;
    setDevMode(newMode);
    localStorage.setItem('scaleflow_dev_mode', String(newMode));
    if (!newMode && activeView !== 'workspace' && activeView !== 'settings') {
      onNavigateToView('workspace');
    }
  };

  // Local sidebar + dev-mode state (not lifted — OK to stay local)

  const { notifications, markAsRead, clearAll } = useNotification();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);

  // Collapsible Developer Tools section
  const [devToolsOpen, setDevToolsOpen] = useState(false);

  // Pipeline telemetry synchronization
  const { selectedPipelineId } = usePipeline();
  const { selectedDocumentId, uploadedFiles } = useDocument();
  const [activePipelineData, setActivePipelineData] = useState(null);

  const activeDoc = uploadedFiles.find(f => f.id === selectedDocumentId);
  const activePipelineStatus = activePipelineData?.pipeline?.status || 'Idle';

  useEffect(() => {
    if (!selectedPipelineId) {
      setActivePipelineData(null);
      return;
    }
    const loadDetails = async () => {
      try {
        const details = await fetchPipelineDetails(selectedPipelineId);
        setActivePipelineData(details);
      } catch (err) {
        console.error('Error fetching pipeline details', err);
      }
    };
    loadDetails();
    const interval = setInterval(loadDetails, 3000);
    return () => clearInterval(interval);
  }, [selectedPipelineId]);

  const handlePrimaryNavigate = (viewId) => {
    if (viewId === 'upload') {
      onNavigateToView('workspace');
      setTimeout(() => {
        const el = document.getElementById('upload-section');
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 100);
    } else if (viewId === 'chat') {
      onNavigateToView('workspace');
      setTimeout(() => {
        const el = document.getElementById('chat-section');
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
    } else if (viewId === 'workspace') {
      onNavigateToView('workspace');
      setTimeout(() => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }, 100);
    } else {
      onNavigateToView(viewId);
    }
    if (isMobile) {
      setSidebarOpen(false);
    }
  };

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
  
  const sidebarClass = isMobile && !sidebarOpen ? 'sidebar-collapsed' : '';
  const appContainerClass = `app-container ${sidebarCollapsed ? 'sidebar-collapsed-layout' : ''}`.trim();

  // Combine infra status for a single system status dot
  const getSystemStatus = () => {
    if (redisStatus === 'online' && dbStatus === 'online' && qdrantStatus === 'online') {
      return { label: 'All systems operational', color: 'var(--color-success)' };
    }
    if (redisStatus === 'offline' && dbStatus === 'offline' && qdrantStatus === 'offline') {
      return { label: 'Systems offline', color: 'var(--color-failure)' };
    }
    return { label: 'Degraded performance', color: 'var(--color-warning)' };
  };
  const systemStatus = getSystemStatus();

  return (
    <div className={appContainerClass} style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg-primary)', color: 'var(--text-primary)' }}>
      
      {/* Mobile Top Navbar with toggles */}
      {isMobile && (
        <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-panel)', padding: 'var(--spacing-12) var(--spacing-16)', borderBottom: '1px solid var(--border-subtle)', zIndex: 100, width: '100%' }}>
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
      <aside className={`sidebar ${sidebarClass}`.trim()} role="navigation" aria-label="Sidebar Navigation" style={{
        width: sidebarCollapsed ? 'var(--sidebar-collapsed-width)' : 'var(--sidebar-width)',
        background: 'var(--bg-panel)',
        borderRight: '1px solid var(--border-subtle)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        padding: '24px 16px',
        flexShrink: 0,
        height: '100vh',
        position: 'sticky',
        top: 0
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
          {!isMobile && (
            <div className="sidebar-branding" style={{ display: 'flex', flexDirection: 'column', gap: '4px', paddingLeft: sidebarCollapsed ? '0' : '8px' }}>
              <div className="sidebar-logo" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Layers size={22} style={{ color: 'var(--color-accent)', flexShrink: 0 }} />
                {!sidebarCollapsed && <span className="sidebar-title-text" style={{ fontSize: '1.15rem', fontWeight: 800, letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>ScaleFlow</span>}
              </div>
              {!sidebarCollapsed && <span className="sidebar-subtitle text-caption" style={{ color: 'var(--text-muted)', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Enterprise Agent Platform</span>}
            </div>
          )}

          <nav className="sidebar-nav" style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {!sidebarCollapsed && (
              <div className="text-caption" style={{ color: 'rgba(255,255,255,0.3)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', fontSize: '9px', marginBottom: '8px', paddingLeft: '8px' }}>
                Primary Navigation
              </div>
            )}
            
            <button 
              className={`sidebar-nav-item ${activeView === 'workspace' ? 'active' : ''}`}
              onClick={() => handlePrimaryNavigate('workspace')}
              data-label="Workspace"
              aria-label="Workspace"
            >
              <Home size={16} />
              <span>Workspace</span>
            </button>

            <button 
              className={`sidebar-nav-item ${activeView === 'upload' ? 'active' : ''}`}
              onClick={() => handlePrimaryNavigate('upload')}
              data-label="Upload"
              aria-label="Upload"
            >
              <UploadCloud size={16} />
              <span>Upload</span>
            </button>

            <button 
              className={`sidebar-nav-item ${activeView === 'documents' ? 'active' : ''}`}
              onClick={() => handlePrimaryNavigate('documents')}
              data-label="Documents"
              aria-label="Documents"
            >
              <Files size={16} />
              <span>Documents</span>
            </button>

            <button 
              className={`sidebar-nav-item ${activeView === 'chat' ? 'active' : ''}`}
              onClick={() => handlePrimaryNavigate('chat')}
              data-label="AI Chat"
              aria-label="AI Chat"
            >
              <MessageSquare size={16} />
              <span>AI Chat</span>
            </button>

            <button 
              className={`sidebar-nav-item ${activeView === 'pipelines' ? 'active' : ''}`}
              onClick={() => handlePrimaryNavigate('pipelines')}
              data-label="Pipeline"
              aria-label="Pipeline"
            >
              <Activity size={16} />
              <span>Pipeline</span>
            </button>

            <button 
              className={`sidebar-nav-item ${activeView === 'benchmarks' ? 'active' : ''}`}
              onClick={() => handlePrimaryNavigate('benchmarks')}
              data-label="Analytics"
              aria-label="Analytics"
            >
              <LineChart size={16} />
              <span>Analytics</span>
            </button>

            <button 
              className={`sidebar-nav-item ${activeView === 'settings' ? 'active' : ''}`}
              onClick={() => handlePrimaryNavigate('settings')}
              data-label="Settings"
              aria-label="Settings"
            >
              <Settings size={16} />
              <span>Settings</span>
            </button>

            {/* Collapsible Developer Tools (Only if devMode === true) */}
            {devMode && (
              <div style={{ marginTop: '20px' }}>
                {!sidebarCollapsed && (
                  <button 
                    onClick={() => setDevToolsOpen(!devToolsOpen)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      width: '100%',
                      background: 'none',
                      border: 'none',
                      padding: '8px',
                      color: 'rgba(255,255,255,0.4)',
                      fontSize: '11px',
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      letterSpacing: '0.05em',
                      cursor: 'pointer',
                      borderRadius: '6px',
                      transition: 'color 0.2s'
                    }}
                  >
                    <span>Developer Tools</span>
                    {devToolsOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                  </button>
                )}

                {(devToolsOpen || sidebarCollapsed) && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', paddingLeft: sidebarCollapsed ? '0' : '8px', marginTop: '6px' }}>
                    <button 
                      className={`sidebar-nav-item ${activeView === 'artifacts' ? 'active' : ''}`}
                      onClick={() => handlePrimaryNavigate('artifacts')}
                      style={{ fontSize: '12px', padding: '8px 12px' }}
                      data-label="Artifacts"
                      aria-label="Artifacts Explorer"
                    >
                      <Database size={14} />
                      <span>Artifacts</span>
                    </button>

                    <button 
                      className={`sidebar-nav-item ${activeView === 'retrieval' ? 'active' : ''}`}
                      onClick={() => handlePrimaryNavigate('retrieval')}
                      style={{ fontSize: '12px', padding: '8px 12px' }}
                      data-label="Retrieval"
                      aria-label="Retrieval Inspector"
                    >
                      <Search size={14} />
                      <span>Retrieval</span>
                    </button>

                    <button 
                      className={`sidebar-nav-item ${activeView === 'infrastructure' ? 'active' : ''}`}
                      onClick={() => handlePrimaryNavigate('infrastructure')}
                      style={{ fontSize: '12px', padding: '8px 12px' }}
                      data-label="Infrastructure"
                      aria-label="Infrastructure Health"
                    >
                      <Cpu size={14} />
                      <span>Infrastructure</span>
                    </button>
                  </div>
                )}
              </div>
            )}
          </nav>
        </div>

        {/* Collapsible toggle / Developer panel switches */}
        <div style={{ borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <button 
            onClick={toggleSidebarCollapse}
            className="sidebar-nav-item"
            style={{ padding: '8px 10px', display: 'flex', justifyContent: sidebarCollapsed ? 'center' : 'flex-start', background: 'transparent' }}
            aria-label={sidebarCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
          >
            {sidebarCollapsed ? <Layout size={16} /> : <ChevronLeft size={16} />}
            {!sidebarCollapsed && <span>Collapse Menu</span>}
          </button>
          
          <button 
            onClick={toggleDevMode}
            style={{
              background: devMode ? 'rgba(59, 130, 246, 0.1)' : 'rgba(255, 255, 255, 0.03)',
              border: devMode ? '1px solid var(--color-accent)' : '1px solid rgba(255,255,255,0.08)',
              color: devMode ? 'var(--color-accent)' : 'var(--text-muted)',
              borderRadius: '6px',
              padding: '6px 12px',
              fontSize: '0.75rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              transition: 'all 0.2s',
              width: '100%'
            }}
            aria-label="Toggle Developer Mode"
          >
            <Eye size={14} />
            {!sidebarCollapsed && (devMode ? 'Dev Mode' : 'User Mode')}
          </button>
        </div>
      </aside>

      {/* 2. MAIN VIEWPORT */}
      <main className="main-viewport" role="main" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflowY: 'auto', height: '100vh', paddingBottom: devPanelOpen ? '280px' : 'var(--drawer-handle-height)' }}>
        
        {/* Top Control Bar */}
        <header className="top-bar" role="banner" style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center', 
          height: 'var(--header-height)', 
          borderBottom: '1px solid var(--border-subtle)', 
          padding: '0 24px', 
          background: 'var(--bg-panel)', 
          position: 'sticky',
          top: 0,
          zIndex: 90
        }}>
          <div className="top-bar-left" style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <span className="text-page-title" style={{ textTransform: 'capitalize' }}>
              {activeView === 'pipelines' ? 'Pipeline' : activeView === 'benchmarks' ? 'Analytics' : activeView}
            </span>
            
            {/* Active Document Status Indicator */}
            {activeDoc && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '0.8rem', background: 'var(--bg-input)', padding: '4px 12px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
                <span className="text-caption" style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>{activeDoc.original_filename}</span>
                <span style={{ width: '1px', height: '12px', background: 'var(--border-subtle)' }} />
                <span className={`status-badge-text text-caption`} style={{ color: activePipelineStatus.toLowerCase() === 'running' ? 'var(--color-pipeline-running)' : 'var(--text-muted)' }}>
                  {activePipelineStatus}
                </span>
              </div>
            )}
          </div>

          <div className="top-bar-right" style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            
            {/* System Status Indicator Dot */}
            <div 
              style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', cursor: 'pointer' }}
              title={`${systemStatus.label} (Redis: ${redisStatus}, DB: ${dbStatus}, Qdrant: ${qdrantStatus})`}
            >
              <span className="status-dot" style={{ background: systemStatus.color, width: '8px', height: '8px' }} />
              <span className="hide-mobile" style={{ color: 'var(--text-secondary)' }}>{systemStatus.color === 'var(--color-success)' ? 'Operational' : 'Issue'}</span>
            </div>

            {/* Global Search Trigger */}
            <button 
              onClick={() => setSearchOpen(true)}
              style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', padding: '8px', transition: 'color 0.2s' }}
              aria-label="Open global search"
            >
              <Search size={18} />
            </button>

            {/* Developer Panel Toggle Button */}
            <button 
              onClick={onToggleDevPanel}
              style={{
                background: devPanelOpen ? 'rgba(59, 130, 246, 0.1)' : 'rgba(255, 255, 255, 0.03)',
                border: devPanelOpen ? '1px solid var(--color-accent)' : '1px solid rgba(255, 255, 255, 0.06)',
                color: devPanelOpen ? 'var(--color-accent)' : 'var(--text-muted)',
                borderRadius: '6px',
                padding: '6px 12px',
                fontSize: '0.75rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                transition: 'all 0.2s'
              }}
              aria-label="Toggle Developer Panel"
            >
              <Terminal size={14} />
              <span className="hide-mobile">Dev Panel</span>
            </button>

            {/* Profile Avatar Trigger (Initials placeholder) */}
            <div 
              style={{
                width: '32px',
                height: '32px',
                borderRadius: 'var(--radius-full)',
                background: 'var(--color-accent)',
                color: 'var(--text-white)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 'bold',
                fontSize: '0.8rem',
                cursor: 'pointer'
              }}
              aria-label="User Profile Menu"
              title="User Profile"
            >
              JD
            </div>
          </div>
        </header>

        {/* Dynamic Inner Children Workspace Pages */}
        <div className="workspace-content" style={{ flex: 1, overflowY: 'visible' }}>
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
