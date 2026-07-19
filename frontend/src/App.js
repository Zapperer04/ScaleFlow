import React, { useState, useEffect } from 'react';
import { 
  ShieldAlert
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
import AppShell from './components/layout/AppShell';
import CommandPalette from './components/ui/CommandPalette';
import ErrorBoundary from './components/ui/ErrorBoundary';
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

  const commandPaletteActions = [
    { id: 'nav-overview', label: 'Go to AI Document Workspace', category: 'Navigation', perform: () => handleNavigateToView('overview') },
    { id: 'nav-pipelines', label: 'Go to DAG Orchestration Workspace', category: 'Navigation', perform: () => handleNavigateToView('pipelines') },
    { id: 'nav-validation', label: 'Go to Validation & Chaos Lab', category: 'Navigation', perform: () => handleNavigateToView('validation-lab') },
    { id: 'nav-workers', label: 'Go to Workers Registry Control', category: 'Navigation', perform: () => handleNavigateToView('workers') },
    { id: 'nav-replay', label: 'Go to Deterministic Replay Engine', category: 'Navigation', perform: () => handleNavigateToView('replay') },
    { id: 'nav-architecture', label: 'Go to System Architecture Blueprint', category: 'Navigation', perform: () => handleNavigateToView('architecture') },
    { id: 'nav-diagnostics', label: 'Go to Diagnostics & Dead-Letter Queue', category: 'Navigation', perform: () => handleNavigateToView('diagnostics') },
    { id: 'nav-design-system', label: 'Go to Design System Showcase', category: 'Navigation', perform: () => handleNavigateToView('design-system') },
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