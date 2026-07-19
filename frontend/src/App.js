import React, { useState, useEffect } from 'react';
import { 
  Layers, Server, Activity, Cpu, RefreshCw, 
  Play, Film, ShieldAlert, Shield, BookOpen
} from 'lucide-react';
import { 
  runIntegrationTests, uploadFile
} from './services/api';
import OverviewPage from './components/OverviewPage';
import PipelineDashboard from './components/PipelineDashboard';
import WorkersPage from './components/WorkersPage';
import ReplayPage from './components/ReplayPage';
import ArchitectureOverview from './components/ArchitectureOverview';
import DiagnosticsPage from './components/DiagnosticsPage';
import TaskModal from './components/TaskModal';
import ValidationLab from './components/ValidationLab';
import DesignSystemShowcase from './components/ui/showcase/DesignSystemShowcase';
import { ThemeProvider } from './contexts/ThemeContext';
import { DocumentProvider, useDocument } from './contexts/DocumentContext';
import { PipelineProvider, usePipeline } from './contexts/PipelineContext';
import { NotificationProvider, useNotification } from './contexts/NotificationContext';
import { useTelemetry } from './services/telemetryStore';
import { pollingManager } from './services/pollingManager';
import './App.css';

const POLL_INTERVAL = parseInt(process.env.REACT_APP_POLL_INTERVAL_MS || "3000");

function AppContent() {
  // Navigation & Views
  const [activeView, setActiveView] = useState('overview');

  // Document State Context
  const { 
    fileType, setFileType, 
    uploading, setUploading, 
    uploadStatus, setUploadStatus 
  } = useDocument();

  // Pipeline State Context
  const { 
    selectedPipelineId, setSelectedPipelineId, 
    pipelines, setPipelines, 
    selectedTaskId, setSelectedTaskId, 
    testing, setTesting, 
    showTestModal, setShowTestModal, 
    testResults, setTestResults 
  } = usePipeline();

  // Notification State Context
  const { 
    showStuckWarning, setShowStuckWarning 
  } = useNotification();

  // Telemetry Store (Outside React Context)
  const workers = useTelemetry(s => s.workers);
  const queueStats = useTelemetry(s => s.queueStats);
  const stats = useTelemetry(s => s.stats);
  const redisStatus = useTelemetry(s => s.redisStatus);
  const dbStatus = useTelemetry(s => s.dbStatus);
  const qdrantStatus = useTelemetry(s => s.qdrantStatus);
  const leaderId = useTelemetry(s => s.leaderId);
  const orchestratorCount = useTelemetry(s => s.orchestratorCount);

  // Poll intervals managed by centralized manager
  useEffect(() => {
    pollingManager.start({
      setPipelines,
      setShowStuckWarning
    }, POLL_INTERVAL);

    return () => {
      pollingManager.stop();
    };
  }, [setPipelines, setShowStuckWarning]);

  const handleRunTests = async () => {
    setTesting(true);
    setTestResults(null);
    setShowTestModal(false);
    try {
      const data = await runIntegrationTests();
      setTestResults(data);
      setShowTestModal(true);
      pollingManager.triggerFastUpdate();
    } catch (err) {
      setTestResults({
        status: 'failed',
        logs: ['Integration test execution failed.'],
        error: err.response?.data || err.message
      });
      setShowTestModal(true);
    } finally {
      setTesting(false);
    }
  };

  const handleUploadFile = async (file) => {
    if (!file) return;
    setUploading(true);
    setUploadStatus('Ingesting file to ScaleFlow...');
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('pipeline_type', fileType);

      const res = await uploadFile(formData);
      setUploadStatus(`Upload success! Started pipeline #${res.pipeline_id}`);
      setSelectedPipelineId(res.pipeline_id);
      
      // Refresh fast data
      pollingManager.triggerFastUpdate();
    } catch (err) {
      console.error('File upload failed:', err);
      setUploadStatus('Upload failed: ' + (err.response?.data?.error || err.message));
    } finally {
      setUploading(false);
    }
  };

  const handleNavigateToView = (viewName) => {
    setActiveView(viewName);
  };

  const handleSelectPipeline = (pipelineId) => {
    setSelectedPipelineId(pipelineId);
    setActiveView('pipelines');
  };

  const getQueuePressure = () => {
    const totalQueued = queueStats.total || 0;
    const maxBacklog = 50;
    return Math.min(100, Math.round((totalQueued / maxBacklog) * 100));
  };

  const queuePressure = getQueuePressure();

  return (
    <div className="app-container">
      
      {/* 1. LEFT SIDEBAR */}
      <aside className="sidebar">
        <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
          <div className="sidebar-branding">
            <div className="sidebar-logo">
              <Layers size={22} />
              <span>ScaleFlow</span>
            </div>
            <span className="sidebar-subtitle">Distributed Platform</span>
          </div>

          <nav className="sidebar-nav">
            <div style={{ color: 'var(--text-muted)', fontSize: '0.65rem', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px', paddingLeft: '8px' }}>
              Main Experience
            </div>
            <button 
              className={`sidebar-nav-item ${activeView === 'overview' ? 'active' : ''}`}
              onClick={() => handleNavigateToView('overview')}
            >
              <Activity size={18} />
              AI Document Workspace
            </button>

            <div style={{ color: 'var(--text-muted)', fontSize: '0.65rem', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.5px', marginTop: '24px', marginBottom: '8px', paddingLeft: '8px' }}>
              Advanced Runtime Tools
            </div>
            <button 
              className={`sidebar-nav-item ${activeView === 'pipelines' ? 'active' : ''}`}
              onClick={() => handleNavigateToView('pipelines')}
            >
              <Play size={18} />
              DAG Orchestration
            </button>
            <button 
              className={`sidebar-nav-item ${activeView === 'validation-lab' ? 'active' : ''}`}
              onClick={() => handleNavigateToView('validation-lab')}
            >
              <Shield size={18} />
              Validation & Chaos Lab
            </button>
            <button 
              className={`sidebar-nav-item ${activeView === 'workers' ? 'active' : ''}`}
              onClick={() => handleNavigateToView('workers')}
            >
              <Server size={18} />
              Workers Registry
            </button>
            <button 
              className={`sidebar-nav-item ${activeView === 'replay' ? 'active' : ''}`}
              onClick={() => handleNavigateToView('replay')}
            >
              <Film size={18} />
              Replay Engine
            </button>
            <button 
              className={`sidebar-nav-item ${activeView === 'architecture' ? 'active' : ''}`}
              onClick={() => handleNavigateToView('architecture')}
            >
              <Layers size={18} />
              System Architecture
            </button>
            
            <button 
              className={`sidebar-nav-item ${activeView === 'diagnostics' ? 'active' : ''}`}
              onClick={() => handleNavigateToView('diagnostics')}
            >
              <ShieldAlert size={18} />
              Diagnostics & DLQ
            </button>
            <button 
              className={`sidebar-nav-item ${activeView === 'design-system' ? 'active' : ''}`}
              onClick={() => handleNavigateToView('design-system')}
            >
              <BookOpen size={18} />
              Design System
            </button>
          </nav>
        </div>

        {/* Cluster Infrastructure Status Footer */}
        <div className="sidebar-footer">
          <div className="cluster-status-title">Infrastructure Health</div>
          <div className="cluster-status-list">
            <div className="cluster-status-item">
              <span>Redis Broker</span>
              <div className="status-dot-container">
                <div className={`status-dot ${redisStatus}`} />
                <span>{redisStatus === 'online' ? 'Connected' : 'Offline'}</span>
              </div>
            </div>
            
            <div className="cluster-status-item">
              <span>Postgres DB</span>
              <div className="status-dot-container">
                <div className={`status-dot ${dbStatus}`} />
                <span>{dbStatus === 'online' ? 'Connected' : 'Offline'}</span>
              </div>
            </div>

            <div className="cluster-status-item">
              <span>Qdrant Store</span>
              <div className="status-dot-container">
                <div className={`status-dot ${qdrantStatus}`} />
                <span>{qdrantStatus === 'online' ? 'Connected' : 'Offline'}</span>
              </div>
            </div>

            <div className="cluster-status-item" style={{ borderTop: '1px solid rgba(255,255,255,0.04)', paddingTop: '8px', marginTop: '4px' }}>
              <span>HA Status</span>
              <span style={{ fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--text-white)' }}>
                {leaderId !== 'Checking...' && leaderId !== 'None' ? 'Leader' : 'Replica'}
              </span>
            </div>

            <div className="cluster-status-item">
              <span>Online Nodes</span>
              <span style={{ fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--color-accent)' }}>
                {workers.filter(w => w.status !== 'offline').length} Workers
              </span>
            </div>
          </div>
        </div>
      </aside>

      {/* 2. MAIN VIEWPORT */}
      <main className="main-viewport">
        
        {/* Top Control Bar */}
        <header className="top-bar">
          <div className="top-bar-left">
            <span className="view-title">
              {activeView === 'overview' && 'Orchestration Control Plane'}
              {activeView === 'pipelines' && 'Active Pipelines Workspace'}
              {activeView === 'validation-lab' && 'System Validation & Chaos Lab'}
              {activeView === 'workers' && 'Worker Registry Control'}
              {activeView === 'vectors' && 'Vector Search Observability'}
              {activeView === 'replay' && 'Deterministic Time Travel Replay'}
              {activeView === 'architecture' && 'ScaleFlow System Architecture'}
              
              {activeView === 'diagnostics' && 'Diagnostics & Dead-Letter Queue'}
            </span>
            
            {/* Cluster pressure or backpressure modes */}
            <span className={`mode-badge ${queuePressure > 60 ? 'backpressure' : queuePressure > 30 ? 'high-load' : ''}`}>
              {queuePressure > 60 ? 'Queue Backpressure: Active' : queuePressure > 30 ? 'Load Mode: High' : 'Load Mode: Optimal'}
            </span>
          </div>

          <div className="top-bar-right">
            <div className="top-bar-stats">
              <div>
                <span>Orchestrators:</span>
                <span className="top-bar-stat-val">{orchestratorCount}</span>
              </div>
              <div style={{ borderLeft: '1px solid rgba(255,255,255,0.1)', paddingLeft: '12px' }}>
                <span>Active Leader ID:</span>
                <span className="top-bar-stat-val" style={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                  {leaderId.length > 10 ? `${leaderId.slice(0, 8)}...` : leaderId}
                </span>
              </div>
              <div style={{ borderLeft: '1px solid rgba(255,255,255,0.1)', paddingLeft: '12px' }}>
                <span>Queue Size:</span>
                <span className="top-bar-stat-val" style={{ color: queuePressure > 60 ? 'var(--color-failure)' : 'var(--text-white)' }}>
                  {queueStats.total || 0}
                </span>
              </div>
            </div>

            <button 
              onClick={handleRunTests}
              disabled={testing}
              className="btn btn-primary"
              style={{
                borderRadius: '4px',
                padding: '8px 16px',
                fontSize: '0.8rem',
                fontWeight: '700',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                background: testing ? 'rgba(91, 140, 255, 0.2)' : 'var(--color-accent)',
                boxShadow: 'none'
              }}
            >
              {testing ? <RefreshCw size={14} className="animate-spin" /> : <Cpu size={14} />}
              Run System Tests
            </button>
          </div>
        </header>

        {/* Global Stuck Queue reconciliation Banner */}
        {showStuckWarning && (
          <div className="alert-banner warning" style={{ borderRadius: 0, borderLeft: 0, borderRight: 0, margin: 0 }}>
            <ShieldAlert size={16} />
            <span className="alert-message">
              Execution queue reconciliation required. Tasks are queued in Redis but worker heartbeat loop is standing by. Check worker registers.
            </span>
          </div>
        )}

        {/* 3. WORKSPACE SCROLL AREA */}
        <div className="workspace-content">
          {activeView === 'overview' && (
            <OverviewPage 
              pipelines={pipelines}
              workers={workers}
              queueStats={queueStats}
              stats={stats}
              redisStatus={redisStatus}
              dbStatus={dbStatus}
              qdrantStatus={qdrantStatus}
              onSelectPipeline={handleSelectPipeline}
              onNavigateToView={handleNavigateToView}
              onUploadFile={handleUploadFile}
              fileType={fileType}
              setFileType={setFileType}
              uploading={uploading}
              uploadStatus={uploadStatus}
              selectedPipelineId={selectedPipelineId}
              setSelectedPipelineId={setSelectedPipelineId}
              onSelectTask={setSelectedTaskId}
            />
          )}

          {activeView === 'pipelines' && (
            <PipelineDashboard 
              selectedPipelineId={selectedPipelineId} 
              setSelectedPipelineId={setSelectedPipelineId} 
            />
          )}

          {activeView === 'workers' && <WorkersPage />}

          {activeView === 'validation-lab' && <ValidationLab />}

          {activeView === 'replay' && <ReplayPage />}

          {activeView === 'architecture' && <ArchitectureOverview />}

          {activeView === 'diagnostics' && <DiagnosticsPage />}

          {activeView === 'design-system' && <DesignSystemShowcase />}
        </div>

      {/* Selected Task Details Modal */}
      <TaskModal 
        taskId={selectedTaskId} 
        onClose={() => setSelectedTaskId(null)} 
        onActionComplete={pollingManager.triggerFastUpdate} 
      />

      {/* System Integration Test Modal */}
      {showTestModal && testResults && (
        <div className="modal-overlay" onClick={() => setShowTestModal(false)} style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(11, 16, 32, 0.8)',
          backdropFilter: 'none',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 1000
        }}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{
            background: 'var(--bg-panel)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '4px',
            width: '90%',
            maxWidth: '650px',
            maxHeight: '80vh',
            display: 'flex',
            flexDirection: 'column',
            boxShadow: 'none',
            color: 'var(--text-primary)'
          }}>
            <div className="modal-header" style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '16px 24px',
              borderBottom: '1px solid var(--border-subtle)'
            }}>
              <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{
                  background: testResults.status === 'success' ? 'var(--color-success)' : 'var(--color-failure)',
                  color: 'var(--text-white)',
                  padding: '4px 10px',
                  borderRadius: '6px',
                  fontSize: '0.75rem',
                  textTransform: 'uppercase',
                  fontWeight: 'bold'
                }}>
                  {testResults.status}
                </span>
                System Integration Test Results
              </h2>
              <button 
                onClick={() => setShowTestModal(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  fontSize: '1.25rem',
                  lineHeight: '1',
                  padding: '4px',
                  borderRadius: '6px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                ✕
              </button>
            </div>
            <div className="modal-body" style={{
              padding: '24px',
              overflowY: 'auto',
              flex: 1,
              fontFamily: 'monospace',
              fontSize: '0.875rem',
              lineHeight: 1.6,
              background: 'var(--bg-primary)'
            }}>
              {testResults.logs && testResults.logs.map((log, index) => {
                let color = 'var(--text-muted-light)';
                if (log.includes('--- Test')) color = 'var(--color-accent)';
                if (log.includes('successfully') || log.includes('passed')) color = 'var(--color-success)';
                if (log.includes('Failed') || log.includes('rejected') || log.includes('error')) color = 'var(--color-failure)';
                
                return (
                  <div key={index} style={{ color, marginBottom: '6px', whiteSpace: 'pre-wrap' }}>
                    {log}
                  </div>
                );
              })}
              {testResults.error && (
                <div style={{ color: 'var(--color-failure)', marginTop: '12px', padding: '12px', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '4px', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
                  <strong>Error:</strong> {JSON.stringify(testResults.error, null, 2)}
                </div>
              )}
            </div>
            <div className="modal-footer" style={{
              padding: '16px 24px',
              borderTop: '1px solid var(--border-subtle)',
              display: 'flex',
              justifyContent: 'flex-end'
            }}>
              <button 
                onClick={() => setShowTestModal(false)}
                className="btn btn-secondary"
                style={{ padding: '8px 20px' }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
      </main>
    </div>
  );
}

function App() {
  return (
    <ThemeProvider>
      <NotificationProvider>
        <DocumentProvider>
          <PipelineProvider>
            <AppContent />
          </PipelineProvider>
        </DocumentProvider>
      </NotificationProvider>
    </ThemeProvider>
  );
}

export default App;