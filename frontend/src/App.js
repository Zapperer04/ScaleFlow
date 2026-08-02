/* eslint-disable no-unused-vars */
import React, { useState, useEffect, lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { 
  ShieldAlert
} from 'lucide-react';
import { 
  runIntegrationTests
} from './services/api';
import WorkspaceHome from './pages/WorkspaceHome';
import DocumentsLibrary from './pages/DocumentsLibrary';
import ArtifactsExplorer from './pages/ArtifactsExplorer';
import RetrievalInspector from './pages/RetrievalInspector';
import SystemBenchmarks from './pages/SystemBenchmarks';
import SystemInfrastructure from './pages/SystemInfrastructure';
import SettingsPage from './pages/SettingsPage';
import TaskModal from './components/TaskModal';
import AppShell from './components/layout/AppShell';
import CommandPalette from './components/ui/CommandPalette';
import ErrorBoundary from './components/ui/ErrorBoundary';
import WorkspaceSkeleton from './components/workspace/WorkspaceSkeleton';
import { ThemeProvider } from './contexts/ThemeContext';
import { DocumentProvider } from './contexts/DocumentContext';
import { PipelineProvider, usePipeline } from './contexts/PipelineContext';
import { NotificationProvider, useNotification } from './contexts/NotificationContext';
import { WorkspaceProvider } from './contexts/WorkspaceContext';
import { useTelemetry } from './services/telemetryStore';
import { pollingManager } from './services/pollingManager';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import PublicLayout from './components/layout/PublicLayout';
import LandingPage from './pages/LandingPage';
import Login from './pages/auth/Login';
import Register from './pages/auth/Register';
import ForgotPassword from './pages/auth/ForgotPassword';
import ResetPassword from './pages/auth/ResetPassword';
import EmailVerification from './pages/auth/EmailVerification';
import NotFound from './pages/NotFound';
import './App.css';

// Lazy-load secondary feature modules
const PipelineDashboard = lazy(() => import('./components/PipelineDashboard'));
const WorkersPage = lazy(() => import('./components/WorkersPage'));
const ReplayPage = lazy(() => import('./components/ReplayPage'));
const ArchitectureOverview = lazy(() => import('./components/ArchitectureOverview'));
const DiagnosticsPage = lazy(() => import('./components/DiagnosticsPage'));
const ValidationLab = lazy(() => import('./components/ValidationLab'));
const DesignSystemShowcase = lazy(() => import('./components/ui/showcase/DesignSystemShowcase'));

const POLL_INTERVAL = parseInt(process.env.REACT_APP_POLL_INTERVAL_MS || "3000");

function AppContent() {
  // Navigation & Views
  const [activeView, setActiveView] = useState('workspace');

  // Developer Panel — lifted here so both AppShell header button and WorkspaceHome
  // BottomDrawer render from the same source of truth
  const [devPanelOpen, setDevPanelOpen] = useState(() => {
    return localStorage.getItem('scaleflow_dev_panel_open') === 'true';
  });
  const toggleDevPanel = () => {
    const next = !devPanelOpen;
    setDevPanelOpen(next);
    localStorage.setItem('scaleflow_dev_panel_open', String(next));
  };


  // Pipeline State Context
  const { 
    selectedPipelineId, setSelectedPipelineId, 
    setPipelines, 
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
  const redisStatus = useTelemetry(s => s.redisStatus);
  const dbStatus = useTelemetry(s => s.dbStatus);
  const qdrantStatus = useTelemetry(s => s.qdrantStatus);
  const leaderId = useTelemetry(s => s.leaderId);
  const orchestratorCount = useTelemetry(s => s.orchestratorCount);

  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);

  // Toggle Command Palette on Cmd+K / Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setCommandPaletteOpen(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

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


  const handleNavigateToView = (viewName) => {
    setActiveView(viewName);
  };


  const getQueuePressure = () => {
    const totalQueued = queueStats.total || 0;
    const maxBacklog = 50;
    return Math.min(100, Math.round((totalQueued / maxBacklog) * 100));
  };

  const queuePressure = getQueuePressure();

  const commandPaletteActions = [
    { id: 'nav-workspace', label: 'Go to Workspace', category: 'Navigation', perform: () => handleNavigateToView('workspace') },
    { id: 'nav-upload', label: 'Go to Upload', category: 'Navigation', perform: () => handleNavigateToView('upload') },
    { id: 'nav-documents', label: 'Go to Documents', category: 'Navigation', perform: () => handleNavigateToView('documents') },
    { id: 'nav-chat', label: 'Go to AI Chat', category: 'Navigation', perform: () => handleNavigateToView('chat') },
    { id: 'nav-pipelines', label: 'Go to Pipeline Monitor', category: 'Navigation', perform: () => handleNavigateToView('pipelines') },
    { id: 'nav-artifacts', label: 'Go to Artifacts Explorer', category: 'Navigation', perform: () => handleNavigateToView('artifacts') },
    { id: 'nav-retrieval', label: 'Go to Retrieval Inspector', category: 'Navigation', perform: () => handleNavigateToView('retrieval') },
    { id: 'nav-benchmarks', label: 'Go to Analytics Dashboard', category: 'Navigation', perform: () => handleNavigateToView('benchmarks') },
    { id: 'nav-infrastructure', label: 'Go to Infrastructure Health', category: 'Navigation', perform: () => handleNavigateToView('infrastructure') },
    { id: 'nav-settings', label: 'Go to Settings', category: 'Navigation', perform: () => handleNavigateToView('settings') },
    { id: 'action-tests', label: 'Execute System Integration Tests', category: 'System Operations', perform: () => handleRunTests() }
  ];

  return (
    <>
      <AppShell
        activeView={activeView}
        onNavigateToView={handleNavigateToView}
        redisStatus={redisStatus}
        dbStatus={dbStatus}
        qdrantStatus={qdrantStatus}
        leaderId={leaderId}
        workers={workers}
        orchestratorCount={orchestratorCount}
        queueStats={queueStats}
        queuePressure={queuePressure}
        testing={testing}
        onRunTests={handleRunTests}
        devPanelOpen={devPanelOpen}
        onToggleDevPanel={toggleDevPanel}
      >
        <ErrorBoundary>
          {showStuckWarning && (
            <div className="alert-banner warning" style={{ borderRadius: 0, borderLeft: 0, borderRight: 0, margin: '0 0 var(--spacing-20) 0' }}>
              <ShieldAlert size={16} />
              <span className="alert-message">
                Execution queue reconciliation required. Tasks are queued in Redis but worker heartbeat loop is standing by. Check worker registers.
              </span>
            </div>
          )}

          <Suspense fallback={<WorkspaceSkeleton />}>
            {activeView === 'workspace' && <WorkspaceHome activeTab="active" devPanelOpen={devPanelOpen} onToggleDevPanel={toggleDevPanel} />}
            
            {activeView === 'upload' && <WorkspaceHome activeTab="upload" devPanelOpen={devPanelOpen} onToggleDevPanel={toggleDevPanel} />}

            {activeView === 'chat' && <WorkspaceHome activeTab="chat" devPanelOpen={devPanelOpen} onToggleDevPanel={toggleDevPanel} />}
            
            {activeView === 'documents' && (
              <DocumentsLibrary onNavigateToView={handleNavigateToView} />
            )}

            {activeView === 'pipelines' && (
              <PipelineDashboard 
                selectedPipelineId={selectedPipelineId} 
                setSelectedPipelineId={setSelectedPipelineId} 
              />
            )}

            {activeView === 'artifacts' && <ArtifactsExplorer />}

            {activeView === 'retrieval' && <RetrievalInspector />}

            {activeView === 'benchmarks' && <SystemBenchmarks />}

            {activeView === 'infrastructure' && <SystemInfrastructure />}

            {activeView === 'settings' && <SettingsPage />}
          </Suspense>
        </ErrorBoundary>
      </AppShell>

      <CommandPalette
        isOpen={commandPaletteOpen}
        onClose={() => setCommandPaletteOpen(false)}
        actions={commandPaletteActions}
      />

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
    </>
  );
}

function ProtectedRoute({ children }) {
  const { token, loading } = useAuth();
  if (loading) {
    return <div style={{ color: 'var(--text-secondary)', padding: 'var(--spacing-32)', fontFamily: 'var(--font-mono)' }}>Restoring session...</div>;
  }
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<PublicLayout><LandingPage /></PublicLayout>} />
          <Route path="/login" element={<PublicLayout><Login /></PublicLayout>} />
          <Route path="/register" element={<PublicLayout><Register /></PublicLayout>} />
          <Route path="/forgot-password" element={<PublicLayout><ForgotPassword /></PublicLayout>} />
          <Route path="/reset-password" element={<PublicLayout><ResetPassword /></PublicLayout>} />
          <Route path="/verify-email" element={<PublicLayout><EmailVerification /></PublicLayout>} />

          {/* Protected Workspace Routes */}
          <Route path="/workspace/*" element={
            <ProtectedRoute>
              <ThemeProvider>
                <NotificationProvider>
                  <DocumentProvider>
                    <PipelineProvider>
                      <WorkspaceProvider>
                        <AppContent />
                      </WorkspaceProvider>
                    </PipelineProvider>
                  </DocumentProvider>
                </NotificationProvider>
              </ThemeProvider>
            </ProtectedRoute>
          } />

          {/* Fallback 404 Route */}
          <Route path="*" element={<PublicLayout><NotFound /></PublicLayout>} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;