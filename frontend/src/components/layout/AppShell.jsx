import React from 'react';
import { 
  Layers, Server, Activity, Cpu, RefreshCw, 
  Play, Film, ShieldAlert, Shield, BookOpen 
} from 'lucide-react';
import Button from '../ui/Button';

/**
 * Reusable layout wrapper for the ScaleFlow application workspace.
 * 
 * @param {Object} props
 * @param {string} props.activeView - Currently rendered route view name
 * @param {Function} props.onNavigateToView - Callback to switch views
 * @param {string} props.redisStatus - Connection state of Redis
 * @param {string} props.dbStatus - Connection state of database
 * @param {string} props.qdrantStatus - Connection state of Qdrant
 * @param {string} props.leaderId - Active orchestrator leader ID
 * @param {Array} props.workers - List of active processing host workers
 * @param {number} props.orchestratorCount - Active leader host count
 * @param {Object} props.queueStats - Queue size and task distributions
 * @param {number} props.queuePressure - Derived queue pressure metric (0-100)
 * @param {boolean} props.testing - Loading lock for tests execution
 * @param {Function} props.onRunTests - Action handler to run system integrations tests
 * @param {React.ReactNode} props.children - Workspace inner page contents
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
  const getNavLabel = () => {
    switch (activeView) {
      case 'overview': return 'Orchestration Control Plane';
      case 'pipelines': return 'Active Pipelines Workspace';
      case 'validation-lab': return 'System Validation & Chaos Lab';
      case 'workers': return 'Worker Registry Control';
      case 'replay': return 'Deterministic Time Travel Replay';
      case 'architecture': return 'ScaleFlow System Architecture';
      case 'diagnostics': return 'Diagnostics & Dead-Letter Queue';
      case 'design-system': return 'Design System Playground';
      default: return 'ScaleFlow Workspace';
    }
  };

  const activeWorkersCount = workers.filter(w => w.status !== 'offline').length;

  return (
    <div className="app-container">
      
      {/* 1. LEFT SIDEBAR */}
      <aside className="sidebar">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-32)' }}>
          <div className="sidebar-branding">
            <div className="sidebar-logo">
              <Layers size={22} style={{ color: 'var(--color-accent)' }} />
              <span className="text-h3" style={{ fontWeight: 'var(--font-weight-heavy)' }}>ScaleFlow</span>
            </div>
            <span className="sidebar-subtitle text-caption">Distributed Platform</span>
          </div>

          <nav className="sidebar-nav">
            <div className="text-caption" style={{ color: 'var(--text-disabled)', fontWeight: 'var(--font-weight-bold)', textTransform: 'uppercase', letterSpacing: 'var(--ls-wide)', marginBottom: 'var(--spacing-8)', paddingLeft: 'var(--spacing-8)' }}>
              Main Experience
            </div>
            <button 
              className={`sidebar-nav-item ${activeView === 'overview' ? 'active' : ''}`}
              onClick={() => onNavigateToView('overview')}
            >
              <Activity size={18} />
              AI Document Workspace
            </button>

            <div className="text-caption" style={{ color: 'var(--text-disabled)', fontWeight: 'var(--font-weight-bold)', textTransform: 'uppercase', letterSpacing: 'var(--ls-wide)', marginTop: 'var(--spacing-24)', marginBottom: 'var(--spacing-8)', paddingLeft: 'var(--spacing-8)' }}>
              Advanced Runtime Tools
            </div>
            <button 
              className={`sidebar-nav-item ${activeView === 'pipelines' ? 'active' : ''}`}
              onClick={() => onNavigateToView('pipelines')}
            >
              <Play size={18} />
              DAG Orchestration
            </button>
            <button 
              className={`sidebar-nav-item ${activeView === 'validation-lab' ? 'active' : ''}`}
              onClick={() => onNavigateToView('validation-lab')}
            >
              <Shield size={18} />
              Validation & Chaos Lab
            </button>
            <button 
              className={`sidebar-nav-item ${activeView === 'workers' ? 'active' : ''}`}
              onClick={() => onNavigateToView('workers')}
            >
              <Server size={18} />
              Workers Registry
            </button>
            <button 
              className={`sidebar-nav-item ${activeView === 'replay' ? 'active' : ''}`}
              onClick={() => onNavigateToView('replay')}
            >
              <Film size={18} />
              Replay Engine
            </button>
            <button 
              className={`sidebar-nav-item ${activeView === 'architecture' ? 'active' : ''}`}
              onClick={() => onNavigateToView('architecture')}
            >
              <Layers size={18} />
              System Architecture
            </button>
            
            <button 
              className={`sidebar-nav-item ${activeView === 'diagnostics' ? 'active' : ''}`}
              onClick={() => onNavigateToView('diagnostics')}
            >
              <ShieldAlert size={18} />
              Diagnostics & DLQ
            </button>
            <button 
              className={`sidebar-nav-item ${activeView === 'design-system' ? 'active' : ''}`}
              onClick={() => onNavigateToView('design-system')}
            >
              <BookOpen size={18} />
              Design System
            </button>
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
      <main className="main-viewport">
        
        {/* Top Control Bar */}
        <header className="top-bar" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', height: '60px', borderBottom: '1px solid var(--border-subtle)', padding: '0 var(--spacing-24)', background: 'var(--bg-panel)' }}>
          <div className="top-bar-left" style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-12)' }}>
            <span className="view-title text-h3" style={{ fontWeight: 'var(--font-weight-bold)', color: 'var(--text-primary)' }}>
              {getNavLabel()}
            </span>
            
            <span className={`mode-badge text-caption ${queuePressure > 60 ? 'backpressure' : queuePressure > 30 ? 'high-load' : ''}`}>
              {queuePressure > 60 ? 'Queue Backpressure: Active' : queuePressure > 30 ? 'Load Mode: High' : 'Load Mode: Optimal'}
            </span>
          </div>

          <div className="top-bar-right" style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-20)' }}>
            <div className="top-bar-stats text-caption" style={{ display: 'flex', gap: 'var(--spacing-16)', color: 'var(--text-secondary)' }}>
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
