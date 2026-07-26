/* eslint-disable no-unused-vars */
import React, { useState, useEffect, useCallback } from 'react';
import { 
  Layers, Cpu, RefreshCw, Menu, X, Bell, Search, Info, 
  CheckCircle2, AlertTriangle, AlertOctagon, Trash2, Eye,
  Home, UploadCloud, Files, MessageSquare, Activity, 
  ChevronDown, ChevronRight, Database, Settings, Terminal, LineChart
} from 'lucide-react';
import Button from '../ui/Button';
import Breadcrumb from '../ui/Breadcrumb';
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
  children
}) => {
  const isMobile = useMediaQuery('(max-width: 768px)');
  const [sidebarOpen, setSidebarOpen] = useState(false);

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

  const { notifications, unreadCount, markAsRead, clearAll } = useNotification();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [infraOpen, setInfraOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);

  // Collapsible Developer Tools section
  const [devToolsOpen, setDevToolsOpen] = useState(false);

  // Pipeline telemetry synchronization
  const { selectedPipelineId } = usePipeline();
  const { selectedDocumentId, uploadedFiles } = useDocument();
  const [activePipelineData, setActivePipelineData] = useState(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  const activeDoc = uploadedFiles.find(f => f.id === selectedDocumentId);
  const activePipelineStatus = activePipelineData?.pipeline?.status || 'Idle';
  const activeWorkersCount = workers.filter(w => w.status !== 'offline').length;

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

  useEffect(() => {
    if (activePipelineStatus.toLowerCase() !== 'running') return;
    const interval = setInterval(() => {
      setElapsedSeconds(prev => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [activePipelineStatus]);

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

  const breadcrumbItems = [
    { label: 'ScaleFlow Workspace', onClick: () => handlePrimaryNavigate('workspace') },
    { label: activeView.charAt(0).toUpperCase() + activeView.slice(1) }
  ];

  const sidebarClass = isMobile && !sidebarOpen ? 'sidebar-collapsed' : '';

  return (
    <div className="app-container" style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg-primary)', color: 'var(--text-primary)' }}>
      
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
        width: '260px',
        background: 'rgba(11, 16, 32, 0.45)',
        backdropFilter: 'blur(20px)',
        borderRight: '1px solid rgba(255, 255, 255, 0.05)',
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
            <div className="sidebar-branding" style={{ display: 'flex', flexDirection: 'column', gap: '4px', paddingLeft: '8px' }}>
              <div className="sidebar-logo" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Layers size={22} style={{ color: 'var(--color-accent)' }} />
                <span style={{ fontSize: '1.15rem', fontWeight: 800, letterSpacing: '-0.02em', background: 'linear-gradient(90deg, #fff 0%, #a5b4fc 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>ScaleFlow</span>
              </div>
              <span className="sidebar-subtitle text-caption" style={{ color: 'var(--text-muted)', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Enterprise Agent Platform</span>
            </div>
          )}

          <nav className="sidebar-nav" style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div className="text-caption" style={{ color: 'rgba(255,255,255,0.3)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', fontSize: '9px', marginBottom: '8px', paddingLeft: '8px' }}>
              Primary Navigation
            </div>
            
            <button 
              className={`sidebar-nav-item ${activeView === 'workspace' ? 'active' : ''}`}
              onClick={() => handlePrimaryNavigate('workspace')}
            >
              <Home size={16} />
              <span>Workspace</span>
            </button>

            <button 
              className="sidebar-nav-item"
              onClick={() => handlePrimaryNavigate('upload')}
            >
              <UploadCloud size={16} />
              <span>Upload Document</span>
            </button>

            <button 
              className={`sidebar-nav-item ${activeView === 'documents' ? 'active' : ''}`}
              onClick={() => handlePrimaryNavigate('documents')}
            >
              <Files size={16} />
              <span>Documents</span>
            </button>

            <button 
              className="sidebar-nav-item"
              onClick={() => handlePrimaryNavigate('chat')}
            >
              <MessageSquare size={16} />
              <span>AI Chat QA</span>
            </button>

            <button 
              className={`sidebar-nav-item ${activeView === 'pipelines' ? 'active' : ''}`}
              onClick={() => handlePrimaryNavigate('pipelines')}
            >
              <Activity size={16} />
              <span>Pipeline Monitor</span>
            </button>

            <button 
              className={`sidebar-nav-item ${activeView === 'benchmarks' ? 'active' : ''}`}
              onClick={() => handlePrimaryNavigate('benchmarks')}
            >
              <LineChart size={16} />
              <span>Analytics</span>
            </button>

            {/* Collapsible Developer Tools */}
            <div style={{ marginTop: '20px' }}>
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

              {devToolsOpen && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', paddingLeft: '8px', marginTop: '6px' }}>
                  <button 
                    className={`sidebar-nav-item ${activeView === 'pipelines' ? 'active' : ''}`}
                    onClick={() => handlePrimaryNavigate('pipelines')}
                    style={{ fontSize: '12px', padding: '8px 12px' }}
                  >
                    <Layers size={14} />
                    <span>Pipeline DAG</span>
                  </button>

                  <button 
                    className={`sidebar-nav-item ${activeView === 'artifacts' ? 'active' : ''}`}
                    onClick={() => handlePrimaryNavigate('artifacts')}
                    style={{ fontSize: '12px', padding: '8px 12px' }}
                  >
                    <Database size={14} />
                    <span>Artifacts Explorer</span>
                  </button>

                  <button 
                    className={`sidebar-nav-item ${activeView === 'retrieval' ? 'active' : ''}`}
                    onClick={() => handlePrimaryNavigate('retrieval')}
                    style={{ fontSize: '12px', padding: '8px 12px' }}
                  >
                    <Search size={14} />
                    <span>Retrieval Inspector</span>
                  </button>

                  <button 
                    className={`sidebar-nav-item ${activeView === 'infrastructure' ? 'active' : ''}`}
                    onClick={() => handlePrimaryNavigate('infrastructure')}
                    style={{ fontSize: '12px', padding: '8px 12px' }}
                  >
                    <Cpu size={14} />
                    <span>Infrastructure</span>
                  </button>

                  <button 
                    className={`sidebar-nav-item ${activeView === 'benchmarks' ? 'active' : ''}`}
                    onClick={() => handlePrimaryNavigate('benchmarks')}
                    style={{ fontSize: '12px', padding: '8px 12px' }}
                  >
                    <LineChart size={14} />
                    <span>Benchmarks</span>
                  </button>

                  <button 
                    className={`sidebar-nav-item ${activeView === 'settings' ? 'active' : ''}`}
                    onClick={() => handlePrimaryNavigate('settings')}
                    style={{ fontSize: '12px', padding: '8px 12px' }}
                  >
                    <Settings size={14} />
                    <span>Settings</span>
                  </button>
                </div>
              )}
            </div>
          </nav>
        </div>

        {/* Brand User Switch */}
        <div style={{ borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <button 
            onClick={toggleDevMode}
            style={{
              background: devMode ? 'rgba(139, 92, 246, 0.1)' : 'rgba(255, 255, 255, 0.03)',
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
          >
            <Eye size={14} />
            {devMode ? 'Developer Mode' : 'User Mode'}
          </button>
        </div>
      </aside>

      {/* 2. MAIN VIEWPORT */}
      <main className="main-viewport" role="main" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflowY: 'auto', height: '100vh' }}>
        
        {/* Top Control Bar */}
        <header className="top-bar" role="banner" style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center', 
          height: '70px', 
          borderBottom: '1px solid rgba(255, 255, 255, 0.05)', 
          padding: '0 24px', 
          background: 'rgba(11, 16, 32, 0.6)', 
          backdropFilter: 'blur(12px)',
          position: 'sticky',
          top: 0,
          zIndex: 90
        }}>
          <div className="top-bar-left" style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <Breadcrumb items={breadcrumbItems} />
            
            {/* Active Document Status Indicator */}
            {activeDoc && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '0.8rem', background: 'rgba(255,255,255,0.02)', padding: '6px 14px', borderRadius: '20px', border: '1px solid rgba(255,255,255,0.05)' }}>
                <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>{activeDoc.original_filename}</span>
                <span style={{ width: '1px', height: '12px', background: 'rgba(255,255,255,0.1)' }} />
                <span className={`status-badge ${activePipelineStatus.toLowerCase()}`} style={{ fontSize: '0.75rem', fontWeight: 700 }}>
                  {activePipelineStatus}
                </span>
                {activePipelineStatus.toLowerCase() === 'running' && (
                  <>
                    <span style={{ width: '1px', height: '12px', background: 'rgba(255,255,255,0.1)' }} />
                    <span style={{ fontFamily: 'monospace', color: 'var(--color-accent)' }}>{elapsedSeconds}s</span>
                  </>
                )}
              </div>
            )}
          </div>

          <div className="top-bar-right" style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            
            {/* Expandable Infrastructure status trigger */}
            <div style={{ position: 'relative' }}>
              <button 
                onClick={() => setInfraOpen(!infraOpen)}
                style={{
                  background: infraOpen ? 'rgba(59, 130, 246, 0.1)' : 'rgba(255, 255, 255, 0.03)',
                  border: infraOpen ? '1px solid var(--color-accent)' : '1px solid rgba(255, 255, 255, 0.06)',
                  color: infraOpen ? 'var(--color-accent)' : 'var(--text-muted)',
                  borderRadius: '6px',
                  padding: '6px 12px',
                  fontSize: '0.75rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  transition: 'all 0.2s'
                }}
              >
                <Cpu size={14} />
                <span>Infra Health {infraOpen ? '▲' : '▼'}</span>
              </button>

              {/* Infrastructure Popover Drawer */}
              {infraOpen && (
                <div style={{
                  position: 'absolute',
                  top: '40px',
                  right: 0,
                  width: '280px',
                  background: 'rgba(15, 23, 42, 0.95)',
                  backdropFilter: 'blur(20px)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: '10px',
                  padding: '16px',
                  boxShadow: '0 12px 32px rgba(0,0,0,0.5)',
                  zIndex: 200,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px'
                }}>
                  <div style={{ fontWeight: 700, fontSize: '0.85rem', color: '#fff', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '8px' }}>
                    System Architecture Health
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.75rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-secondary)' }}>Redis Broker</span>
                      <span style={{ color: redisStatus === 'online' ? 'var(--color-success)' : 'var(--color-failure)', fontWeight: 600 }}>{redisStatus === 'online' ? 'Online' : 'Offline'}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-secondary)' }}>Postgres DB</span>
                      <span style={{ color: dbStatus === 'online' ? 'var(--color-success)' : 'var(--color-failure)', fontWeight: 600 }}>{dbStatus === 'online' ? 'Online' : 'Offline'}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-secondary)' }}>Qdrant Vector</span>
                      <span style={{ color: qdrantStatus === 'online' ? 'var(--color-success)' : 'var(--color-failure)', fontWeight: 600 }}>{qdrantStatus === 'online' ? 'Online' : 'Offline'}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '8px' }}>
                      <span style={{ color: 'var(--text-secondary)' }}>HA Role</span>
                      <span style={{ color: '#fff', fontWeight: 600 }}>{leaderId !== 'Checking...' && leaderId !== 'None' ? 'Active Leader' : 'Replica Node'}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-secondary)' }}>Orchestrators</span>
                      <span style={{ color: '#fff', fontWeight: 600 }}>{orchestratorCount}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-secondary)' }}>Active Workers</span>
                      <span style={{ color: 'var(--color-accent)', fontWeight: 600 }}>{activeWorkersCount} Online</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-secondary)' }}>Queue Length</span>
                      <span style={{ color: '#fff', fontWeight: 600 }}>{queueStats.total || 0}</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Global Search Trigger */}
            <button 
              onClick={() => setSearchOpen(true)}
              style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', padding: '8px', transition: 'color 0.2s' }}
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
                    width: '15px',
                    height: '15px',
                    fontSize: '0.6rem',
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

            {devMode && (
              <Button 
                variant="primary" 
                onClick={onRunTests}
                disabled={testing}
                iconLeft={testing ? <RefreshCw size={14} className="animate-spin" /> : <Cpu size={14} />}
                style={{ borderRadius: '6px', fontSize: '0.75rem', padding: '6px 14px' }}
              >
                Run Tests
              </Button>
            )}
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
