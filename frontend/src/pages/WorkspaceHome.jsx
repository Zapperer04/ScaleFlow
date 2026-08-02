/* eslint-disable no-unused-vars */
import React, { useState, useEffect, useRef, useMemo } from 'react';
import { 
  Send, FileText, CheckCircle2, AlertTriangle, Play, HelpCircle, 
  ChevronRight, ChevronDown, Download, Layers, ShieldAlert, Cpu, 
  Terminal, BarChart, ZoomIn, ZoomOut, Search, Compass, RefreshCw, Upload, Eye
} from 'lucide-react';
import { usePipeline } from '../contexts/PipelineContext';
import { useDocument } from '../contexts/DocumentContext';
import { useWorkspace } from '../contexts/WorkspaceContext';
import { useNotification } from '../contexts/NotificationContext';
import { 
  createQueryPipelineV1, 
  fetchQueryPipelineAnswerV1,
  explainQueryPipeline
} from '../services/search';
import { fetchUploadedFiles, fetchPdfContent } from '../services/documents';
import { fetchPipelineDetails, fetchPipelineTimeline, cancelPipeline, retryPipeline } from '../services/pipelines';
import { apiClient } from '../services/apiClient';
import ProgressBar from '../components/ui/ProgressBar';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import { ExecutionConsole } from '../components/workspace/logs/ExecutionConsole';
import { ErrorPanel } from '../components/workspace/logs/ErrorPanel';
import { PipelineControls } from '../components/workspace/pipeline/PipelineControls';
import { PipelineHeader } from '../components/workspace/pipeline/PipelineHeader';
import { PipelineDAG } from '../components/workspace/pipeline/PipelineDAG';
import { PerformanceTimeline } from '../components/workspace/timeline/PerformanceTimeline';
import { FlameGraph } from '../components/workspace/timeline/FlameGraph';
import { WorkerUtilizationChart } from '../components/workspace/timeline/WorkerUtilizationChart';
import { StageBreakdown } from '../components/workspace/timeline/StageBreakdown';
import { OptimizationTab } from '../components/workspace/timeline/OptimizationTab';
import { ForecastTab } from '../components/workspace/timeline/ForecastTab';
import { SchedulingAdvisorTab } from '../components/workspace/timeline/SchedulingAdvisorTab';
import { QueryWorkbench } from '../components/workspace/documents/QueryWorkbench';
import { RetrievalInspector } from './RetrievalInspector';
import { GraphExplorer } from '../components/workspace/documents/GraphExplorer';
import { CitationViewer } from '../components/workspace/documents/CitationViewer';
import { DocumentViewer } from '../components/workspace/documents/DocumentViewer';


export const WorkspaceHome = ({ activeTab }) => {
  const { 
    selectedPipelineId, setSelectedPipelineId, pipelines,
    timelineEvents, timelineLoading, timelineError,
    refreshTrigger, onRetryTask,
    selectedTaskId, setSelectedTaskId,
    selectedTraceId, setSelectedTraceId,
    selectedWorkerId, setSelectedWorkerId,
    replayMode, replayIndex, replaySnapshots,
    comparisonMode, loadPerformance,
    performanceModel, performanceLoading, performanceError,
    optimizationModel, optimizationLoading, optimizationError,
    loadOptimization,
    forecastModel, forecastLoading, forecastError, loadForecast,
    loadAdvisor
  } = usePipeline();
  const { selectedDocumentId, setSelectedDocumentId, uploadedFiles, setUploadedFiles } = useDocument();
  const { selectDocument } = useWorkspace();

  // Local UX States
  const [activeCenterTab, setActiveCenterTab] = useState('query'); // 'query' | 'inspector' | 'graph' | 'citation' | 'pdf'
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [rightInspectorCollapsed, setRightInspectorCollapsed] = useState(false);
  const [bottomDrawerCollapsed, setBottomDrawerCollapsed] = useState(true);
  const [bottomTab, setBottomTab] = useState('dag'); // 'dag' | 'artifacts'
  
  // Tabs for the Explainability Drawer
  const [explainTab, setExplainTab] = useState('evidence'); // 'evidence' | 'pipeline' | 'prompt' | 'metrics'

  // Multi-document state
  const [selectedDocIds, setSelectedDocIds] = useState([]);

  // Workspace View State Machine: 'blank' | 'timeline' | 'ready' | 'chatting'
  const [workspaceState, setWorkspaceState] = useState('blank');

  // Chat States
  const [chatQuery, setChatQuery] = useState('');
  const [chatThread, setChatThread] = useState([
    {
      role: 'assistant',
      content: 'Welcome! Choose or upload a document from the left library rail, and ask any question to inspect hybrid retrieval logic.',
      timestamp: new Date().toLocaleTimeString()
    }
  ]);
  
  // Streaming Query Pipeline States
  const [activeQueryPipelineId, setActiveQueryPipelineId] = useState(null);
  const [currentQueryStage, setCurrentQueryStage] = useState(''); // 'intent' | 'embedding' | 'vector' | 'graph' | 'bm25' | 'fusion' | 'prompt' | 'llm' | 'completed'
  const [queryTimer, setQueryTimer] = useState(0.0);
  const [explainPayload, setExplainPayload] = useState(null);
  const [activeAnswerDetails, setActiveAnswerDetails] = useState(null);

  // PDF Preview State
  const [zoomLevel, setZoomLevel] = useState(100);
  const [activePdfPage, setActivePdfPage] = useState(1);
  const [highlightText, setHighlightText] = useState('');
  const [highlights, setHighlights] = useState([]); // Array of coordinate boxes

  // Active Ingestion Pipeline Telemetry
  const [activeDag, setActiveDag] = useState(null);
  const [selectedDagNode, setSelectedDagNode] = useState(null);

  // Server-side document summary metadata from GET /pipelines/{id}/metadata
  const [pipelineMetadata, setPipelineMetadata] = useState(null);

  // pdf.js state
  const canvasRef = useRef(null);
  const [pdfDoc, setPdfDoc] = useState(null);
  const threadEndRef = useRef(null);

  // Load documents library
  useEffect(() => {
    const loadFiles = async () => {
      try {
        const filesList = await fetchUploadedFiles();
        setUploadedFiles(filesList || []);
      } catch (err) {
        console.error("Error loading files", err);
      }
    };
    loadFiles();
    const interval = setInterval(loadFiles, 5000);
    return () => clearInterval(interval);
  }, [setUploadedFiles]);

  // Restore states from localStorage
  useEffect(() => {
    const docId = localStorage.getItem('scaleflow_active_doc');
    const zoom = localStorage.getItem('scaleflow_zoom');
    const page = localStorage.getItem('scaleflow_pdf_page');
    if (docId) setSelectedDocumentId(parseInt(docId));
    if (zoom) setZoomLevel(parseInt(zoom));
    if (page) setActivePdfPage(parseInt(page));
  }, [setSelectedDocumentId]);

  // Load performance, optimization & forecast model once per replay session when tab is opened
  useEffect(() => {
    if (bottomTab === 'performance' && replayMode) {
      loadPerformance();
    } else if (bottomTab === 'optimization' && replayMode) {
      loadOptimization();
    } else if (bottomTab === 'forecast' && replayMode) {
      loadForecast();
    } else if (bottomTab === 'advisor' && replayMode) {
      loadAdvisor();
    }
  }, [bottomTab, replayMode, selectedPipelineId, loadPerformance, loadOptimization, loadForecast, loadAdvisor]);

  useEffect(() => {
    if (activeTab === 'upload') {
      setWorkspaceState('blank');
      return;
    }
    if (activeTab === 'chat' && selectedDocumentId) {
      setWorkspaceState('chatting');
      setActiveCenterTab('query');
    }
  }, [activeTab, selectedDocumentId]);

  useEffect(() => {
    if (!selectedDocumentId) {
      setWorkspaceState('blank');
      return;
    }
    localStorage.setItem('scaleflow_active_doc', selectedDocumentId);

    // Find the associated pipeline by file_id or doc.pipeline_id
    const doc = uploadedFiles.find(f => f.id === selectedDocumentId);
    const assoc = pipelines.find(p =>
      p.file_id === selectedDocumentId ||
      (doc && (p.file_id === doc.id || p.id === doc.pipeline_id))
    );

    if (assoc) {
      setSelectedPipelineId(assoc.id);
      const backendStatus = assoc.status?.toLowerCase();
      if (backendStatus === 'completed') {
        // Only transition to ready/chatting when backend confirms completion.
        // Preserve 'chatting' if user already opened chat for this completed pipeline.
        setWorkspaceState(prev => (prev === 'chatting' ? 'chatting' : 'ready'));
      } else {
        // Any non-completed status (running, pending, failed, paused) → show timeline
        setWorkspaceState('timeline');
      }
    } else {
      // No matching pipeline found yet (e.g., just uploaded, polling hasn't returned it).
      // Stay on timeline so the UI shows a loading state rather than jumping to ready.
      setWorkspaceState('timeline');
    }
  }, [selectedDocumentId, uploadedFiles, pipelines, setSelectedPipelineId]);

  useEffect(() => {
    localStorage.setItem('scaleflow_zoom', zoomLevel);
  }, [zoomLevel]);

  useEffect(() => {
    localStorage.setItem('scaleflow_pdf_page', activePdfPage);
  }, [activePdfPage]);

  // Load PDF file via pdfjs
  useEffect(() => {
    if (!selectedDocumentId) {
      setPdfDoc(null);
      return;
    }
    const loadPdf = async () => {
      try {
        const blob = await fetchPdfContent(selectedDocumentId);
        const arrayBuffer = await blob.arrayBuffer();
        const pdfjs = await import('pdfjs-dist/build/pdf');
        pdfjs.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.mjs';
        const loadingTask = pdfjs.getDocument({ data: arrayBuffer });
        const pdf = await loadingTask.promise;
        setPdfDoc(pdf);
        setActivePdfPage(1);
      } catch (err) {
        console.error("Error loading PDF via pdfjs-dist", err);
      }
    };
    loadPdf();
  }, [selectedDocumentId]);

  // Render canvas page
  useEffect(() => {
    if (!pdfDoc || !canvasRef.current) return;
    const renderPage = async () => {
      try {
        const page = await pdfDoc.getPage(activePdfPage);
        const viewport = page.getViewport({ scale: zoomLevel / 100 });
        const canvas = canvasRef.current;
        const context = canvas.getContext('2d');
        canvas.height = viewport.height;
        canvas.width = viewport.width;

        const renderContext = {
          canvasContext: context,
          viewport: viewport
        };
        await page.render(renderContext).promise;
      } catch (err) {
        console.error("Error rendering PDF page", err);
      }
    };
    renderPage();
  }, [pdfDoc, activePdfPage, zoomLevel]);

  // Fetch ingestion pipeline details (tasks, artifacts, status) & server metadata every 3s
  useEffect(() => {
    if (!selectedPipelineId) {
      setActiveDag(null);
      setPipelineMetadata(null);
      return;
    }
    if (replayMode) {
      // Pause DAG refresh during replay mode
      return;
    }
    const loadDag = async () => {
      try {
        const details = await fetchPipelineDetails(selectedPipelineId);
        setActiveDag(details);
      } catch (e) {
        console.error('fetchPipelineDetails failed', e);
      }
      try {
        const metaRes = await apiClient.get(`/pipelines/${selectedPipelineId}/metadata`);
        setPipelineMetadata(metaRes.data);
      } catch (e) {
        // Metadata endpoint might return 404 if pipeline has no metadata yet
      }
    };
    loadDag();
    const interval = setInterval(loadDag, 3000);
    return () => clearInterval(interval);
  }, [selectedPipelineId, refreshTrigger, replayMode]);

  // Derived Replay-aware DAG state
  const currentActiveDag = useMemo(() => {
    if (!replayMode || !replaySnapshots || replayIndex < 0 || !activeDag) {
      return activeDag;
    }
    const snapshot = replaySnapshots[replayIndex];
    const replayedTasks = (activeDag.tasks || []).map(t => {
      const snapTask = snapshot.taskStates[String(t.id)];
      return snapTask ? {
        ...t,
        status: snapTask.status,
        assigned_worker_id: snapTask.workerId,
        retry_count: snapTask.retryCount
      } : t;
    });

    return {
      ...activeDag,
      pipeline: {
        ...activeDag.pipeline,
        status: replayedTasks.every(t => t.status === 'completed') ? 'completed' : replayedTasks.some(t => t.status === 'failed') ? 'failed' : 'running'
      },
      tasks: replayedTasks
    };
  }, [replayMode, replaySnapshots, replayIndex, activeDag]);



  // Query Execution Stage Timer
  useEffect(() => {
    if (!currentQueryStage || currentQueryStage === 'completed') return;
    const timer = setInterval(() => {
      setQueryTimer(prev => prev + 0.05);
    }, 50);
    return () => clearInterval(timer);
  }, [currentQueryStage]);

  // Load explain metrics
  const fetchAnswerExplain = async (pipelineId) => {
    try {
      const exp = await explainQueryPipeline(pipelineId);
      setExplainPayload(exp);
      const ans = await fetchQueryPipelineAnswerV1(pipelineId);
      setActiveAnswerDetails(ans);
    } catch (e) {
      console.error("Error fetching explain metrics", e);
    }
  };

  // Submit Chat Query (SSE Stream)
  const handleSendQuery = async (e) => {
    e.preventDefault();
    if (!chatQuery.trim()) return;

    const userMsg = chatQuery;
    setChatQuery('');
    setQueryTimer(0.0);
    
    setChatThread(prev => [
      ...prev,
      { role: 'user', content: userMsg, timestamp: new Date().toLocaleTimeString() }
    ]);

    const tempMsgId = 'stream-answer-' + Date.now();
    setChatThread(prev => [
      ...prev,
      { id: tempMsgId, role: 'assistant', content: 'Processing query...', isStreaming: true, timestamp: new Date().toLocaleTimeString() }
    ]);

    try {
      setCurrentQueryStage('intent');
      const qpPayload = {
        query: userMsg,
        top_k: 5,
        document_ids: selectedDocIds.length > 0 ? selectedDocIds : [selectedDocumentId]
      };
      
      const res = await createQueryPipelineV1(qpPayload);
      const pipeId = res.pipeline_id;
      setActiveQueryPipelineId(pipeId);

      setCurrentQueryStage('embedding');
      const eventSource = new EventSource(`${process.env.REACT_APP_API_URL || 'http://127.0.0.1:5000'}/api/v1/query-pipelines/${pipeId}/stream`);
      let answerAccumulator = '';
      
      eventSource.addEventListener('stage', (event) => {
        const data = JSON.parse(event.data);
        if (data.stage === 'retrieving') {
          setCurrentQueryStage('vector');
        } else if (data.stage === 'reranking') {
          setCurrentQueryStage('fusion');
        } else if (data.stage === 'generating') {
          setCurrentQueryStage('llm');
        }
      });

      eventSource.addEventListener('token', (event) => {
        const data = JSON.parse(event.data);
        answerAccumulator += data.token;
        setChatThread(prev => 
          prev.map(m => m.id === tempMsgId ? { ...m, content: answerAccumulator } : m)
        );
      });

      eventSource.addEventListener('completed', (event) => {
        eventSource.close();
        setCurrentQueryStage('completed');
        fetchAnswerExplain(pipeId);
      });

      eventSource.addEventListener('error', (event) => {
        eventSource.close();
        setCurrentQueryStage('completed');
        setChatThread(prev => 
          prev.map(m => m.id === tempMsgId ? { ...m, content: 'Streaming connection encountered an error.', isError: true } : m)
        );
      });
      
    } catch (err) {
      setCurrentQueryStage('completed');
      setChatThread(prev => [
        ...prev.filter(m => m.id !== tempMsgId),
        { role: 'assistant', content: `Error: ${err.message}`, isError: true, timestamp: new Date().toLocaleTimeString() }
      ]);
    }
  };

  const handleCitationClick = (citation) => {
    setActiveCenterTab('pdf');
    if (citation.page !== undefined) {
      setActivePdfPage(citation.page);
    }
    if (citation.bounding_box) {
      setHighlights([citation.bounding_box]);
    } else {
      setHighlights([{ x: 50, y: 80, width: 250, height: 30, page: citation.page || 1 }]);
    }
    if (citation.chunk_text) {
      setHighlightText(citation.chunk_text);
    }
  };

  const handleToggleDocSelect = (docId) => {
    setSelectedDocIds(prev => 
      prev.includes(docId) ? prev.filter(id => id !== docId) : [...prev, docId]
    );
  };

  const handleSelectDoc = (doc) => {
    setSelectedDocumentId(doc.id);
    selectDocument(doc.id);
  };

  const activeDoc = uploadedFiles.find(f => f.id === selectedDocumentId);

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 60px)', background: 'var(--bg-primary)', overflow: 'hidden' }}>
      
      {/* 1. LEFT SIDEBAR: Document selection rail */}
      <div 
        style={{ 
          width: sidebarCollapsed ? '0px' : '260px', 
          borderRight: '1px solid var(--border-subtle)', 
          background: 'var(--bg-panel)',
          display: 'flex',
          flexDirection: 'column',
          transition: 'width 0.3s ease',
          overflow: 'hidden',
          flexShrink: 0
        }}
      >
        <div style={{ padding: '16px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ margin: 0, fontSize: '0.875rem', fontWeight: 700 }}>Workspace Documents</h3>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '10px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {uploadedFiles.map(doc => {
            const isSelected = selectedDocumentId === doc.id;
            const isChecked = selectedDocIds.includes(doc.id);
            return (
              <div 
                key={doc.id}
                style={{
                  padding: '10px 12px',
                  borderRadius: '6px',
                  background: isSelected ? 'rgba(139, 92, 246, 0.08)' : 'transparent',
                  border: isSelected ? '1px solid rgba(139, 92, 246, 0.2)' : '1px solid transparent',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}
              >
                <input 
                  type="checkbox" 
                  checked={isChecked}
                  onChange={() => handleToggleDocSelect(doc.id)}
                  style={{ cursor: 'pointer' }}
                />
                <div onClick={() => handleSelectDoc(doc)} style={{ flex: 1, textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap', fontSize: '0.8rem' }}>
                  {doc.original_filename}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 2. CENTER PANEL: Chat and PDF viewport */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        
        {/* Workspace Tab Header */}
        <div style={{ display: 'flex', background: 'var(--bg-panel)', borderBottom: '1px solid var(--border-subtle)', padding: '0 16px', justifyContent: 'space-between', alignItems: 'center', height: '48px' }}>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button 
              onClick={() => setActiveCenterTab('query')}
              style={{
                background: 'none',
                border: 'none',
                borderBottom: activeCenterTab === 'query' ? '2px solid var(--color-accent)' : '2px solid transparent',
                color: activeCenterTab === 'query' ? 'var(--text-primary)' : 'var(--text-muted)',
                padding: '12px 16px',
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: '0.8rem'
              }}
            >
              Query Workbench
            </button>
            <button 
              onClick={() => setActiveCenterTab('inspector')}
              style={{
                background: 'none',
                border: 'none',
                borderBottom: activeCenterTab === 'inspector' ? '2px solid var(--color-accent)' : '2px solid transparent',
                color: activeCenterTab === 'inspector' ? 'var(--text-primary)' : 'var(--text-muted)',
                padding: '12px 16px',
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: '0.8rem'
              }}
            >
              Retrieval Inspector
            </button>
            <button 
              onClick={() => setActiveCenterTab('graph')}
              style={{
                background: 'none',
                border: 'none',
                borderBottom: activeCenterTab === 'graph' ? '2px solid var(--color-accent)' : '2px solid transparent',
                color: activeCenterTab === 'graph' ? 'var(--text-primary)' : 'var(--text-muted)',
                padding: '12px 16px',
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: '0.8rem'
              }}
            >
              Graph Explorer
            </button>
            <button 
              onClick={() => setActiveCenterTab('citation')}
              style={{
                background: 'none',
                border: 'none',
                borderBottom: activeCenterTab === 'citation' ? '2px solid var(--color-accent)' : '2px solid transparent',
                color: activeCenterTab === 'citation' ? 'var(--text-primary)' : 'var(--text-muted)',
                padding: '12px 16px',
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: '0.8rem'
              }}
            >
              Citation Viewer
            </button>
            <button 
              onClick={() => setActiveCenterTab('pdf')}
              style={{
                background: 'none',
                border: 'none',
                borderBottom: activeCenterTab === 'pdf' ? '2px solid var(--color-accent)' : '2px solid transparent',
                color: activeCenterTab === 'pdf' ? 'var(--text-primary)' : 'var(--text-muted)',
                padding: '12px 16px',
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: '0.8rem'
              }}
            >
              Document Viewer
            </button>
          </div>
        </div>

        {/* Viewport content */}
        <div style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
          
          {workspaceState === 'blank' && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', padding: '40px', gap: '20px' }}>
              <Upload size={48} style={{ color: 'var(--text-disabled)' }} />
              <div style={{ textAlign: 'center' }}>
                <h3 style={{ margin: 0, fontWeight: 700 }}>Drag & Drop PDF</h3>
                <p style={{ margin: '4px 0 0 0', fontSize: '0.8rem', color: 'var(--text-muted)' }}>Select or upload a file to begin indexing.</p>
              </div>
              <div style={{ width: '100%', maxWidth: '400px', background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '16px', marginTop: '20px' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--text-disabled)', textTransform: 'uppercase' }}>Recent Documents</span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '10px' }}>
                  {uploadedFiles.map(doc => (
                    <button 
                      key={doc.id}
                      onClick={() => handleSelectDoc(doc)}
                      style={{ background: 'none', border: 'none', textAlign: 'left', color: 'var(--color-accent)', cursor: 'pointer', fontSize: '0.8rem', padding: 0 }}
                    >
                      📁 {doc.original_filename}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {workspaceState === 'timeline' && (
            <div style={{ padding: '32px', overflowY: 'auto', height: '100%' }}>
              {/* Pipeline header — all values from backend; nothing invented */}
              {currentActiveDag && currentActiveDag.pipeline && (
                <div style={{ marginBottom: '20px' }}>
                  <PipelineHeader
                    pipelineId={selectedPipelineId}
                    documentName={activeDoc?.original_filename}
                    workerId={currentActiveDag.tasks?.find(t => t.status === 'running')?.assigned_worker_id || 'Unassigned'}
                    status={currentActiveDag.pipeline.status}
                    elapsedSeconds={currentActiveDag.pipeline.started_at ? Math.round((new Date(currentActiveDag.pipeline.completed_at || new Date().toISOString()) - new Date(currentActiveDag.pipeline.started_at)) / 1000) : 0}
                    queuePosition={currentActiveDag.tasks?.find(t => t.status === 'pending')?.queue_position || null}
                    startTime={currentActiveDag.pipeline.started_at}
                  />
                </div>
              )}

              <h3 style={{ margin: '0 0 16px 0', fontSize: '1rem', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
                [ {activeDoc?.original_filename || 'Untitled'} — Ingestion Pipeline ]
              </h3>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', maxWidth: '800px' }}>
                {currentActiveDag?.tasks?.length > 0 ? (
                  currentActiveDag.tasks.map((task, idx) => {
                    const inputArtifacts = (currentActiveDag.artifacts || []).filter(art => (task.input_artifact_ids || []).includes(art.id));
                    const outputArtifacts = (currentActiveDag.artifacts || []).filter(art => (task.output_artifact_ids || []).includes(art.id));
                    
                    // Retrieve pre-calculated backend validation status
                    const failedValidation = outputArtifacts.find(art => art.metadata_json?.validation?.is_valid === false);
                    const validationError = failedValidation ? failedValidation.metadata_json?.validation?.error_message : null;
                    const isSelected = selectedTaskId === task.id;

                    const handleCardClick = () => {
                      if (isSelected) {
                        setSelectedTaskId(null);
                        setSelectedTraceId(null);
                        setSelectedWorkerId(null);
                      } else {
                        setSelectedTaskId(task.id);
                        let cid = null;
                        if (task.payload && typeof task.payload === 'object') {
                          cid = task.payload.correlation_id;
                        }
                        if (!cid && task.data) {
                          try {
                            const parsed = JSON.parse(task.data);
                            cid = parsed.correlation_id;
                          } catch (_) {}
                        }
                        setSelectedTraceId(cid || null);
                        setSelectedWorkerId(task.assigned_worker_id || task.worker_id || null);
                      }
                    };

                    return (
                      <div 
                        key={idx} 
                        onClick={handleCardClick}
                        style={{ 
                          padding: '16px', 
                          border: isSelected 
                            ? '2.5px solid #a78bfa' 
                            : (failedValidation ? '1px solid var(--color-failure)' : '1px solid var(--border-subtle)'), 
                          borderRadius: '12px', 
                          background: 'var(--bg-panel)',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '12px',
                          boxShadow: isSelected ? '0 4px 12px rgba(167, 139, 250, 0.2)' : 'var(--shadow-sm)',
                          cursor: 'pointer',
                          transition: 'border 0.15s, box-shadow 0.15s',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div>
                            <div style={{ fontWeight: 700, fontSize: '0.9rem', color: '#fff' }}>{task.type || task.task_type}</div>
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-disabled)', fontFamily: 'var(--font-mono)' }}>
                              ID: #{task.id} | Worker: {task.assigned_worker_id || 'Not Available'}
                            </span>
                          </div>
                          <div style={{ display: 'flex', gap: '8px' }}>
                            {/* Execution Status Badge */}
                            <Badge variant={task.status === 'completed' ? 'success' : task.status === 'failed' ? 'failure' : 'warning'}>
                              EXEC: {task.status?.toUpperCase() || 'QUEUED'}
                            </Badge>
                            {/* Validation Status Badge */}
                            {task.status === 'completed' && (
                              <Badge variant={failedValidation ? 'failure' : 'success'}>
                                VAL: {failedValidation ? 'FAILED' : 'PASSED'}
                              </Badge>
                            )}
                          </div>
                        </div>

                        {/* Lineage metrics grid */}
                        <div style={{ 
                          display: 'grid', 
                          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', 
                          gap: '12px', 
                          fontSize: '0.75rem', 
                          fontFamily: 'var(--font-mono)',
                          color: 'var(--text-secondary)',
                          borderTop: '1px solid rgba(255,255,255,0.04)',
                          paddingTop: '12px'
                        }}>
                          <div>Started: <strong style={{ color: '#fff' }}>{task.started_at ? new Date(task.started_at).toLocaleTimeString() : 'Not Available'}</strong></div>
                          <div>Finished: <strong style={{ color: '#fff' }}>{task.completed_at ? new Date(task.completed_at).toLocaleTimeString() : 'Not Available'}</strong></div>
                          <div>Duration: <strong style={{ color: '#fff' }}>{task.execution_duration != null ? `${task.execution_duration}s` : 'Not Available'}</strong></div>
                          <div>Queue Wait: <strong style={{ color: '#fff' }}>{task.queue_wait_duration != null ? `${task.queue_wait_duration}s` : 'Not Available'}</strong></div>
                          <div>Retries: <strong style={{ color: '#fff' }}>{task.retry_count} / {task.max_retries}</strong></div>
                        </div>

                        {/* Server-derived validation error message display */}
                        {failedValidation && (
                          <div style={{ 
                            color: 'var(--color-failure)', 
                            fontSize: '0.75rem', 
                            fontFamily: 'var(--font-mono)', 
                            background: 'rgba(244,63,94,0.06)', 
                            border: '1px solid rgba(244,63,94,0.15)', 
                            padding: '10px 14px', 
                            borderRadius: '8px',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '4px'
                          }}>
                            <div><strong>Server Validation Failure:</strong> {validationError || 'Semantic checks failed.'}</div>
                            <div style={{ fontSize: '0.7rem', color: 'var(--text-disabled)' }}>
                              Code: {failedValidation.metadata_json?.validation?.error_code || 'N/A'} | 
                              Version: v{failedValidation.metadata_json?.validation?.validator_version || '1'} | 
                              Validated At: {failedValidation.metadata_json?.validation?.validated_at ? new Date(failedValidation.metadata_json.validation.validated_at).toLocaleTimeString() : 'N/A'}
                            </div>
                          </div>
                        )}

                        {/* Input & Output lineage artifacts listing */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.75rem', borderTop: '1px solid rgba(255,255,255,0.04)', paddingTop: '10px' }}>
                          {inputArtifacts.length > 0 && (
                            <div>
                              <span style={{ color: 'var(--text-disabled)', fontWeight: 600 }}>Input Artifacts:</span>
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '4px' }}>
                                {inputArtifacts.map((art, aIdx) => (
                                  <span key={aIdx} style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
                                    📁 {art.artifact_type} (URI: {art.storage_uri || 'Not Available'}) | Hash: {art.checksum || 'Not Available'}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                          {outputArtifacts.length > 0 && (
                            <div style={{ marginTop: '4px' }}>
                              <span style={{ color: 'var(--text-disabled)', fontWeight: 600 }}>Output Artifacts:</span>
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '4px' }}>
                                {outputArtifacts.map((art, aIdx) => (
                                  <span key={aIdx} style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
                                    📁 {art.artifact_type} (URI: {art.storage_uri || 'Not Available'}) | Hash: {art.checksum || 'Not Available'}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                    {currentActiveDag ? 'No tasks reported by backend yet.' : 'Loading pipeline data...'}
                  </div>
                )}
              </div>

              {/* Pipeline action controls — wired to backend endpoints */}
              {currentActiveDag && currentActiveDag.pipeline && (
                <div style={{ marginTop: '24px' }}>
                  <PipelineControls
                    status={currentActiveDag.pipeline.status}
                    onPause={null}  /* Backend pause endpoint not yet available */
                    onResume={null} /* Backend resume endpoint not yet available */
                    onCancel={async () => {
                      try { await cancelPipeline(selectedPipelineId); } catch (e) { console.error('cancel failed', e); }
                    }}
                    onRetry={async () => {
                      try { await retryPipeline(selectedPipelineId); } catch (e) { console.error('retry failed', e); }
                    }}
                    onReupload={() => setWorkspaceState('blank')}
                    onDelete={null} /* Delete endpoint not yet implemented */
                  />
                </div>
              )}
            </div>
          )}

          {workspaceState === 'ready' && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', padding: '40px', gap: '16px' }}>
              <CheckCircle2 size={48} style={{ color: 'var(--color-success)' }} />
              <div style={{ textAlign: 'center' }}>
                <h3 style={{ margin: 0, fontWeight: 700 }}>✓ Document Indexed Successfully</h3>
                <p style={{ margin: '4px 0 0 0', fontSize: '0.8rem', color: 'var(--text-muted)' }}>The parsing pipeline is ready.</p>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', width: '100%', maxWidth: '520px', background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '20px', fontSize: '0.8rem' }}>
                <div>Pages: <strong>{activeDoc?.page_count || pipelineMetadata?.summary?.pages || 'Not Available'}</strong></div>
                <div>Chunks: <strong>{pipelineMetadata?.chunk_count || (currentActiveDag?.artifacts || []).find(a => a.artifact_type === 'graph_chunks')?.metadata_json?.chunk_count || 'Not Available'}</strong></div>
                <div>Embeddings: <strong>{pipelineMetadata?.embedding_count || (currentActiveDag?.artifacts || []).find(a => a.artifact_type === 'graph_embeddings')?.metadata_json?.total_embeddings || 'Not Available'}</strong></div>
                <div>Graph Nodes: <strong>{(currentActiveDag?.artifacts || []).find(a => a.artifact_type === 'document_graph')?.metadata_json?.stats?.node_count || 'Not Available'}</strong></div>
                <div>Graph Edges: <strong>{(currentActiveDag?.artifacts || []).find(a => a.artifact_type === 'document_graph')?.metadata_json?.stats?.edge_count || 'Not Available'}</strong></div>
                <div>Processing Time: <strong>{(currentActiveDag?.artifacts || []).find(a => a.artifact_type === 'graph_embeddings')?.metadata_json?.embedding_generation_duration ? `${Math.round((currentActiveDag?.artifacts || []).find(a => a.artifact_type === 'graph_embeddings')?.metadata_json?.embedding_generation_duration)}s` : 'Not Available'}</strong></div>
              </div>
              <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
                <Button
                  variant="primary"
                  onClick={() => setWorkspaceState('chatting')}
                  disabled={currentActiveDag?.status?.toLowerCase() !== 'completed'}
                >
                  Open Chat
                </Button>
                <Button variant="secondary" onClick={() => { setWorkspaceState('chatting'); setActiveCenterTab('pdf'); }}>View Document</Button>
              </div>
            </div>
          )}

          {workspaceState === 'chatting' && activeCenterTab === 'query' && (
            <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
              <QueryWorkbench />
            </div>
          )}

          {workspaceState === 'chatting' && activeCenterTab === 'inspector' && (
            <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
              <RetrievalInspector />
            </div>
          )}

          {workspaceState === 'chatting' && activeCenterTab === 'graph' && (
            <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
              <GraphExplorer />
            </div>
          )}

          {workspaceState === 'chatting' && activeCenterTab === 'citation' && (
            <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
              <CitationViewer />
            </div>
          )}

          {workspaceState === 'chatting' && activeCenterTab === 'pdf' && (
            <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
              <DocumentViewer />
            </div>
          )}
        </div>

        {/* Collapsible Bottom Drawer */}
        <div style={{ borderTop: '1px solid var(--border-subtle)', background: 'var(--bg-panel)', padding: '6px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', gap: '16px' }}>
            <button onClick={() => { setBottomDrawerCollapsed(false); setBottomTab('dag'); }} style={{ background: 'none', border: 'none', color: bottomTab === 'dag' ? 'var(--color-accent)' : 'var(--text-muted)', fontSize: '0.75rem', cursor: 'pointer', fontWeight: 600 }}>Pipeline Visual DAG</button>
            <button onClick={() => { setBottomDrawerCollapsed(false); setBottomTab('artifacts'); }} style={{ background: 'none', border: 'none', color: bottomTab === 'artifacts' ? 'var(--color-accent)' : 'var(--text-muted)', fontSize: '0.75rem', cursor: 'pointer', fontWeight: 600 }}>Artifact Explorer</button>
            {replayMode && (
              <>
                <button onClick={() => { setBottomDrawerCollapsed(false); setBottomTab('performance'); }} style={{ background: 'none', border: 'none', color: bottomTab === 'performance' ? 'var(--color-accent)' : 'var(--text-muted)', fontSize: '0.75rem', cursor: 'pointer', fontWeight: 600 }}>Performance Analytics</button>
                <button onClick={() => { setBottomDrawerCollapsed(false); setBottomTab('optimization'); }} style={{ background: 'none', border: 'none', color: bottomTab === 'optimization' ? 'var(--color-accent)' : 'var(--text-muted)', fontSize: '0.75rem', cursor: 'pointer', fontWeight: 600 }}>Optimization</button>
                <button onClick={() => { setBottomDrawerCollapsed(false); setBottomTab('forecast'); }} style={{ background: 'none', border: 'none', color: bottomTab === 'forecast' ? 'var(--color-accent)' : 'var(--text-muted)', fontSize: '0.75rem', cursor: 'pointer', fontWeight: 600 }}>Forecast</button>
                <button onClick={() => { setBottomDrawerCollapsed(false); setBottomTab('advisor'); }} style={{ background: 'none', border: 'none', color: bottomTab === 'advisor' ? 'var(--color-accent)' : 'var(--text-muted)', fontSize: '0.75rem', cursor: 'pointer', fontWeight: 600 }}>Scheduling Advisor</button>
              </>
            )}
          </div>
          <button onClick={() => setBottomDrawerCollapsed(!bottomDrawerCollapsed)} style={{ background: 'none', border: 'none', color: 'var(--text-primary)', cursor: 'pointer', fontSize: '0.75rem' }}>
            {bottomDrawerCollapsed ? '▲ Open Drawer' : '▼ Close'}
          </button>
        </div>

        <div style={{ height: bottomDrawerCollapsed ? '0px' : '360px', transition: 'height 0.3s ease', borderTop: bottomDrawerCollapsed ? 'none' : '1px solid var(--border-subtle)', background: 'var(--bg-panel)', overflow: 'hidden' }}>
          {bottomTab === 'dag' ? (
            <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px', height: '100%', overflow: 'auto' }}>
              {/* Dynamic Pipeline DAG Flowchart */}
              <div>
                <span style={{ fontSize: '0.8rem', fontWeight: 'bold', display: 'block', marginBottom: '8px' }}>Pipeline Visual DAG (Frozen MR-RAG Flow)</span>
                <PipelineDAG
                  tasks={currentActiveDag?.tasks || []}
                  artifacts={currentActiveDag?.artifacts || []}
                  selectedNodeId={selectedDagNode?.id}
                  onSelectNode={(node) => setSelectedDagNode(node)}
                />
              </div>

              {/* Task Badges Lineage */}
              <div>
                <span style={{ fontSize: '0.8rem', fontWeight: 'bold' }}>Pipeline Task Stages</span>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '10px' }}>
                  {currentActiveDag?.tasks?.length > 0 ? (
                    currentActiveDag.tasks.map((task, idx) => (
                      <Badge
                        key={idx}
                        variant={task.status === 'completed' ? 'success' : task.status === 'failed' ? 'failure' : 'warning'}
                        onClick={() => setSelectedDagNode(task)}
                        style={{ cursor: 'pointer' }}
                      >
                        {task.task_type}: {task.status}
                      </Badge>
                    ))
                  ) : (
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {selectedPipelineId ? 'Awaiting backend task data...' : 'No active pipeline'}
                    </span>
                  )}
                </div>
              </div>

              {/* Execution Console — real logs from /pipelines/{id}/timeline */}
              <ExecutionConsole 
                events={timelineEvents} 
                loading={timelineLoading} 
                error={timelineError} 
              />

              {/* Error Panel — derived from failed backend tasks, no hardcoded errors */}
              {(comparisonMode || currentActiveDag?.tasks?.some(t => t.status === 'failed' || t.status === 'cancelled')) && (
                <ErrorPanel
                  errors={(currentActiveDag.tasks || [])
                    .filter(t => t.status === 'failed' || t.status === 'cancelled')
                    .map(t => {
                      const sortTimestamp = t.completed_at || t.updated_at || t.created_at || '';
                      const displayTime = sortTimestamp
                        ? new Date(sortTimestamp).toLocaleString()
                        : 'Not Available';
                      return {
                        id:                t.id,
                        level:             'error',
                        status:            t.status,
                        message:           t.error_message || `${t.type} stage failed`,
                        stage:             t.type || 'Not Available',
                        worker:            t.assigned_worker_id ?? 'Not Available',
                        retries:           t.retry_count !== undefined ? t.retry_count : 0,
                        maxRetries:        t.max_retries !== undefined ? t.max_retries : 3,
                        queueWait:         t.queue_wait_duration !== undefined ? t.queue_wait_duration : 'Not Available',
                        executionDuration: t.execution_duration !== undefined ? t.execution_duration : 'Not Available',
                        timestamp:         displayTime,
                        sortTimestamp:     sortTimestamp ? new Date(sortTimestamp).getTime() : 0,
                      };
                    })
                    .sort((a, b) => {
                      // 1. Newest timestamp first
                      if (b.sortTimestamp !== a.sortTimestamp) {
                        return b.sortTimestamp - a.sortTimestamp;
                      }
                      // 2. Highest retry count first
                      if (b.retries !== a.retries) {
                        return b.retries - a.retries;
                      }
                      // 3. Stage name order (alphabetical fallback)
                      return a.stage.localeCompare(b.stage);
                    })}
                  onRetryTask={onRetryTask}
                />
              )}
            </div>
          ) : bottomTab === 'artifacts' ? (
            <div style={{ padding: '16px', overflow: 'auto', height: '100%' }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 'bold' }}>Pipeline Artifact Files</span>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '12px' }}>
                {currentActiveDag?.artifacts?.length > 0 ? (
                  currentActiveDag.artifacts.map((artifact, idx) => {
                    const sizeKB = artifact.size_bytes ? `(${Math.round(artifact.size_bytes / 1024)} KB)` : '';
                    return (
                      <span key={idx} style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        📁 {artifact.artifact_type || artifact.name || `artifact-${idx}`} {sizeKB}
                      </span>
                    );
                  })
                ) : (
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    {selectedPipelineId ? 'No artifacts reported by backend yet.' : 'No active pipeline.'}
                  </span>
                )}
              </div>
            </div>
          ) : bottomTab === 'performance' ? (
            <div style={{ padding: '16px', overflow: 'auto', height: '100%', display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 'bold' }}>Performance Analytics</span>
              
              {/* Load/Error states */}
              {timelineLoading && (
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Analyzing pipeline execution latency...</div>
              )}
              {performanceError && (
                <div style={{ fontSize: '0.75rem', color: 'var(--color-danger)' }}>{performanceError}</div>
              )}
              
              {!timelineLoading && !performanceError && performanceModel && (
                <>
                  <PerformanceTimeline />
                  <FlameGraph />
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', minWidth: '800px' }}>
                    <WorkerUtilizationChart workers={performanceModel.performance.workers} />
                    <StageBreakdown stages={performanceModel.performance.stages} />
                  </div>
                </>
              )}
            </div>
          ) : bottomTab === 'optimization' ? (
            <div style={{ padding: '16px', overflow: 'auto', height: '100%', display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 'bold' }}>Performance Recommendations & Simulation</span>
              <OptimizationTab 
                key={optimizationModel?.pipeline_id || 'no-pipeline'}
                optimizationModel={optimizationModel}
                loading={optimizationLoading}
                error={optimizationError}
              />
            </div>
          ) : bottomTab === 'forecast' ? (
            <div style={{ padding: '16px', overflow: 'auto', height: '100%', display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 'bold' }}>Predictive Execution Forecasting</span>
              <ForecastTab />
            </div>
          ) : (
            <div style={{ padding: '16px', overflow: 'auto', height: '100%', display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 'bold' }}>Adaptive Scheduling Advisor</span>
              <SchedulingAdvisorTab />
            </div>
          )}
        </div>

      </div>

      {/* 3. RIGHT INSPECTOR: Retrieval explainability */}
      <div 
        style={{ 
          width: rightInspectorCollapsed ? '0px' : '320px', 
          borderLeft: '1px solid var(--border-subtle)', 
          background: 'var(--bg-panel)',
          display: 'flex',
          flexDirection: 'column',
          transition: 'width 0.3s ease',
          overflow: 'hidden',
          flexShrink: 0
        }}
      >
        <div style={{ padding: '16px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ margin: 0, fontSize: '0.875rem', fontWeight: 700 }}>Explainability</h3>
        </div>

        {/* Tab Headers inside the drawer */}
        <div style={{ display: 'flex', borderBottom: '1px solid var(--border-subtle)', background: 'var(--bg-primary)' }}>
          {['evidence', 'pipeline', 'prompt', 'metrics'].map(tab => (
            <button
              key={tab}
              onClick={() => setExplainTab(tab)}
              style={{
                flex: 1,
                background: 'none',
                border: 'none',
                borderBottom: explainTab === tab ? '2px solid var(--color-accent)' : '2px solid transparent',
                color: explainTab === tab ? 'var(--text-primary)' : 'var(--text-muted)',
                padding: '8px 0',
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer',
                textTransform: 'capitalize'
              }}
            >
              {tab}
            </button>
          ))}
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {explainTab === 'evidence' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <span style={{ fontSize: '0.7rem', fontWeight: 'bold', color: 'var(--text-disabled)', textTransform: 'uppercase' }}>Sources Used</span>
                <div style={{ marginTop: '8px', background: 'var(--bg-primary)', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '12px', fontSize: '0.8rem', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {/* All values from activeAnswerDetails returned by the query pipeline explain endpoint.
                      If a field is absent, we show 'Not Available' — never a fabricated value. */}
                  <div>[✓] Vector: <strong>{activeAnswerDetails?.vector_chunks != null ? `${activeAnswerDetails.vector_chunks} chunks` : 'Not Available'}</strong></div>
                  <div>[✓] Graph: <strong>{activeAnswerDetails?.graph_nodes != null ? `${activeAnswerDetails.graph_nodes} nodes` : 'Not Available'}</strong></div>
                  <div>[✓] BM25: <strong>{activeAnswerDetails?.bm25_matches != null ? `${activeAnswerDetails.bm25_matches} matches` : 'Not Available'}</strong></div>
                  <div>Fusion: <strong>{activeAnswerDetails?.fusion_contexts != null ? `${activeAnswerDetails.fusion_contexts} contexts` : 'Not Available'}</strong></div>
                  <div>Prompt: <strong>{activeAnswerDetails?.prompt_tokens != null ? `${activeAnswerDetails.prompt_tokens} tokens` : 'Not Available'}</strong></div>
                </div>
              </div>
            </div>
          )}

          {explainTab === 'pipeline' && (
            <div>
              <span style={{ fontSize: '0.7rem', fontWeight: 'bold', color: 'var(--text-disabled)', textTransform: 'uppercase' }}>Retrieval Flow</span>
              {/* Retrieval steps from explainPayload returned by /query-pipelines/{id}/explain */}
              {explainPayload?.retrieval_steps?.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '10px', fontSize: '0.75rem', borderLeft: '2px solid var(--border-subtle)', paddingLeft: '12px' }}>
                  {explainPayload.retrieval_steps.map((step, idx) => (
                    <div key={idx}>✓ {step}</div>
                  ))}
                </div>
              ) : (
                <div style={{ marginTop: '10px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {activeQueryPipelineId ? 'Not Available' : 'Submit a query to inspect retrieval flow.'}
                </div>
              )}
            </div>
          )}

          {explainTab === 'prompt' && (
            <div>
              <span style={{ fontSize: '0.7rem', fontWeight: 'bold', color: 'var(--text-disabled)', textTransform: 'uppercase' }}>Prompt Context</span>
              <pre style={{ marginTop: '8px', background: 'var(--bg-primary)', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '10px', fontSize: '0.7rem', overflowX: 'auto', whiteSpace: 'pre-wrap', color: 'var(--text-secondary)' }}>
                {explainPayload?.final_prompt_context || (activeQueryPipelineId ? 'Not Available' : 'Submit a query to load prompt context.')}
              </pre>
            </div>
          )}

          {explainTab === 'metrics' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <span style={{ fontSize: '0.7rem', fontWeight: 'bold', color: 'var(--text-disabled)', textTransform: 'uppercase' }}>Expert Heatmap Score</span>
                {/* Scores from explainPayload.expert_scores; fallback to Not Available */}
                {explainPayload?.expert_scores ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '8px' }}>
                    {Object.entries(explainPayload.expert_scores).map(([key, val]) => (
                      <div key={key}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '2px' }}>
                          <span>{key}</span>
                          <span>{typeof val === 'number' ? val.toFixed(3) : val}</span>
                        </div>
                        {typeof val === 'number' && <ProgressBar progress={Math.round(val * 100)} variant="success" />}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ marginTop: '10px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    {activeQueryPipelineId ? 'Not Available' : 'Submit a query to inspect expert scores.'}
                  </div>
                )}
              </div>
            </div>
          )}

        </div>
      </div>

    </div>
  );
};

export default WorkspaceHome;
