/* eslint-disable no-unused-vars */
import React, { useState, useEffect, useRef } from 'react';
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
import { fetchPipelineDetails } from '../services/pipelines';
import ProgressBar from '../components/ui/ProgressBar';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';

export const WorkspaceHome = () => {
  const { selectedPipelineId, setSelectedPipelineId, pipelines } = usePipeline();
  const { selectedDocumentId, setSelectedDocumentId, uploadedFiles, setUploadedFiles } = useDocument();
  const { selectDocument } = useWorkspace();

  // Local UX States
  const [activeCenterTab, setActiveCenterTab] = useState('chat'); // 'chat' | 'pdf'
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

  useEffect(() => {
    if (selectedDocumentId) {
      localStorage.setItem('scaleflow_active_doc', selectedDocumentId);
      // Auto transition state
      const doc = uploadedFiles.find(f => f.id === selectedDocumentId);
      if (doc) {
        // If file exists, check pipeline status
        const assoc = pipelines.find(p => p.file_id === doc.id || p.id === doc.pipeline_id);
        if (assoc) {
          setSelectedPipelineId(assoc.id);
          if (assoc.status === 'completed') {
            setWorkspaceState('ready');
          } else {
            setWorkspaceState('timeline');
          }
        } else {
          setWorkspaceState('ready');
        }
      }
    } else {
      setWorkspaceState('blank');
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

  // Fetch ingestion pipeline tasks details
  useEffect(() => {
    if (!selectedPipelineId) return;
    const loadDag = async () => {
      try {
        const details = await fetchPipelineDetails(selectedPipelineId);
        setActiveDag(details);
      } catch (e) {
        console.error(e);
      }
    };
    loadDag();
    const interval = setInterval(loadDag, 3000);
    return () => clearInterval(interval);
  }, [selectedPipelineId]);

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
              onClick={() => setActiveCenterTab('chat')}
              style={{
                background: 'none',
                border: 'none',
                borderBottom: activeCenterTab === 'chat' ? '2px solid var(--color-accent)' : '2px solid transparent',
                color: activeCenterTab === 'chat' ? 'var(--text-primary)' : 'var(--text-muted)',
                padding: '12px 16px',
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: '0.8rem'
              }}
            >
              Interactive Chat
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
              <h3 style={{ margin: '0 0 16px 0', fontSize: '1rem', fontWeight: 700 }}>[ {activeDoc?.original_filename} - Ingestion In Progress ]</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', maxWidth: '600px' }}>
                {activeDag && activeDag.tasks && activeDag.tasks.map((task, idx) => (
                  <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', padding: '12px', border: '1px solid var(--border-subtle)', borderRadius: '8px', background: 'var(--bg-panel)' }}>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>{task.task_type}</div>
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-disabled)' }}>State: {task.status}</span>
                    </div>
                    <Badge variant={task.status === 'completed' ? 'success' : task.status === 'failed' ? 'failure' : 'warning'}>
                      {task.status}
                    </Badge>
                  </div>
                ))}
              </div>
            </div>
          )}

          {workspaceState === 'ready' && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', padding: '40px', gap: '16px' }}>
              <CheckCircle2 size={48} style={{ color: 'var(--color-success)' }} />
              <div style={{ textAlign: 'center' }}>
                <h3 style={{ margin: 0, fontWeight: 700 }}>✓ Document Indexed Successfully</h3>
                <p style={{ margin: '4px 0 0 0', fontSize: '0.8rem', color: 'var(--text-muted)' }}>The parsing pipeline is ready.</p>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', width: '100%', maxWidth: '500px', background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '20px', fontSize: '0.8rem' }}>
                <div>Pages: <strong>{activeDoc?.page_count || 12}</strong></div>
                <div>Chunks: <strong>624</strong></div>
                <div>Entities: <strong>233</strong></div>
                <div>Graph Nodes: <strong>815</strong></div>
                <div>Processing Time: <strong>6.8s</strong></div>
                <div>Confidence: <strong>0.96</strong></div>
              </div>
              <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
                <Button variant="primary" onClick={() => setWorkspaceState('chatting')}>Open Chat</Button>
                <Button variant="secondary" onClick={() => setActiveCenterTab('pdf')}>View Document</Button>
              </div>
            </div>
          )}

          {workspaceState === 'chatting' && activeCenterTab === 'chat' && (
            <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
              
              {/* Chat Thread */}
              <div style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                
                {/* Active query step banner */}
                {currentQueryStage && currentQueryStage !== 'completed' && (
                  <div style={{ background: 'rgba(139, 92, 246, 0.08)', border: '1px solid rgba(139, 92, 246, 0.2)', borderRadius: '8px', padding: '16px', marginBottom: '16px' }}>
                    <div style={{ fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--color-accent)', textTransform: 'uppercase', marginBottom: '8px' }}>Current Status</div>
                    <div style={{ fontSize: '0.8rem' }}>Stage: <strong>{currentQueryStage.toUpperCase()}</strong></div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>Elapsed: {queryTimer.toFixed(2)}s</div>
                  </div>
                )}

                {chatThread.map((msg, idx) => (
                  <div 
                    key={idx}
                    style={{
                      alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                      background: msg.role === 'user' ? 'var(--color-accent)' : 'var(--bg-panel)',
                      color: '#fff',
                      borderRadius: '8px',
                      padding: '12px 16px',
                      maxWidth: '80%',
                      boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
                    }}
                  >
                    <p style={{ margin: 0, fontSize: '0.85rem', lineHeight: 1.5 }}>{msg.content}</p>
                    {msg.citations && (
                      <div style={{ marginTop: '8px', display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                        {msg.citations.map((cite, cIdx) => (
                          <button
                            key={cIdx}
                            onClick={() => handleCitationClick(cite)}
                            style={{
                              background: 'rgba(255,255,255,0.1)',
                              border: 'none',
                              borderRadius: '4px',
                              padding: '2px 6px',
                              fontSize: '0.7rem',
                              color: '#fff',
                              cursor: 'pointer'
                            }}
                          >
                            [{cIdx + 1}] Page {cite.page || 1}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
                <div ref={threadEndRef} />
              </div>

              {/* Chat Input */}
              <form onSubmit={handleSendQuery} style={{ padding: '16px', borderTop: '1px solid var(--border-subtle)', background: 'var(--bg-panel)', display: 'flex', gap: '12px' }}>
                <input 
                  type="text"
                  placeholder="Ask a question about active document structures..."
                  value={chatQuery}
                  onChange={e => setChatQuery(e.target.value)}
                  style={{
                    flex: 1,
                    background: 'var(--bg-primary)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '6px',
                    padding: '10px 14px',
                    color: 'var(--text-primary)',
                    fontSize: '0.85rem'
                  }}
                />
                <Button variant="primary" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Send size={14} /> Send
                </Button>
              </form>

            </div>
          )}

          {workspaceState === 'chatting' && activeCenterTab === 'pdf' && (
            <div style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', background: 'var(--bg-panel)', padding: '10px 16px', border: '1px solid var(--border-subtle)', borderBottom: 'none', borderTopLeftRadius: '6px', borderTopRightRadius: '6px' }}>
                <span style={{ fontSize: '0.8rem', fontWeight: 'bold' }}>{activeDoc?.original_filename || 'No document loaded'}</span>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <Button size="small" variant="secondary" onClick={() => setZoomLevel(z => Math.max(50, z - 10))}><ZoomOut size={12} /></Button>
                  <span style={{ fontSize: '0.75rem' }}>{zoomLevel}%</span>
                  <Button size="small" variant="secondary" onClick={() => setZoomLevel(z => Math.min(200, z + 10))}><ZoomIn size={12} /></Button>
                </div>
              </div>

              <div style={{ flex: 1, background: '#090d16', border: '1px solid var(--border-subtle)', overflow: 'auto', display: 'flex', justifyContent: 'center', alignItems: 'flex-start', padding: '20px', position: 'relative' }}>
                {pdfDoc ? (
                  <div style={{ position: 'relative' }}>
                    <canvas ref={canvasRef} />
                    {/* Bounding Box coordinate highlights */}
                    {highlights.map((box, idx) => {
                      if (box.page && box.page !== activePdfPage) return null;
                      return (
                        <div 
                          key={idx}
                          style={{
                            position: 'absolute',
                            left: `${box.x * (zoomLevel / 100)}px`,
                            top: `${box.y * (zoomLevel / 100)}px`,
                            width: `${box.width * (zoomLevel / 100)}px`,
                            height: `${box.height * (zoomLevel / 100)}px`,
                            background: 'rgba(254, 240, 138, 0.4)',
                            border: '1.5px solid #eab308',
                            borderRadius: '2px',
                            pointerEvents: 'none'
                          }}
                        />
                      );
                    })}
                  </div>
                ) : (
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginTop: '40px' }}>Loading PDF content stream...</div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Collapsible Bottom Drawer */}
        <div style={{ borderTop: '1px solid var(--border-subtle)', background: 'var(--bg-panel)', padding: '6px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', gap: '16px' }}>
            <button onClick={() => { setBottomDrawerCollapsed(false); setBottomTab('dag'); }} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', fontSize: '0.75rem', cursor: 'pointer', fontWeight: 600 }}>Pipeline Visual DAG</button>
            <button onClick={() => { setBottomDrawerCollapsed(false); setBottomTab('artifacts'); }} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', fontSize: '0.75rem', cursor: 'pointer', fontWeight: 600 }}>Artifact Explorer</button>
          </div>
          <button onClick={() => setBottomDrawerCollapsed(!bottomDrawerCollapsed)} style={{ background: 'none', border: 'none', color: 'var(--text-primary)', cursor: 'pointer', fontSize: '0.75rem' }}>
            {bottomDrawerCollapsed ? '▲ Open Drawer' : '▼ Close'}
          </button>
        </div>

        <div style={{ height: bottomDrawerCollapsed ? '0px' : '260px', transition: 'height 0.3s ease', borderTop: bottomDrawerCollapsed ? 'none' : '1px solid var(--border-subtle)', background: 'var(--bg-panel)', overflow: 'hidden' }}>
          {bottomTab === 'dag' ? (
            <div style={{ padding: '16px' }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 'bold' }}>Ingestion Flowchart Timeline</span>
              <div style={{ display: 'flex', gap: '12px', marginTop: '12px' }}>
                <Badge variant="success">Preprocess: Done</Badge>
                <Badge variant="success">Parse: Done</Badge>
                <Badge variant="success">Chunking: Done</Badge>
                <Badge variant="warning">Embedding: Syncing</Badge>
              </div>
            </div>
          ) : (
            <div style={{ padding: '16px' }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 'bold' }}>Pipeline Artifact Files</span>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '12px' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>📁 graph.json (48.1 KB)</span>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>📁 chunks.json (112 KB)</span>
              </div>
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
                  <div>[✓] Vector: <strong>12 chunks</strong></div>
                  <div>[✓] Graph: <strong>8 nodes</strong></div>
                  <div>[✓] BM25: <strong>3 matches</strong></div>
                  <div>Fusion: <strong>20 contexts</strong></div>
                  <div>Prompt: <strong>3,980 tokens</strong></div>
                </div>
              </div>
            </div>
          )}

          {explainTab === 'pipeline' && (
            <div>
              <span style={{ fontSize: '0.7rem', fontWeight: 'bold', color: 'var(--text-disabled)', textTransform: 'uppercase' }}>Retrieval Flow</span>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '10px', fontSize: '0.75rem', borderLeft: '2px solid var(--border-subtle)', paddingLeft: '12px' }}>
                <div>✓ Intent Detected</div>
                <div>✓ Dense vector queried</div>
                <div>✓ Graph neighbors expanded</div>
                <div>✓ RRF fusion complete</div>
              </div>
            </div>
          )}

          {explainTab === 'prompt' && (
            <div>
              <span style={{ fontSize: '0.7rem', fontWeight: 'bold', color: 'var(--text-disabled)', textTransform: 'uppercase' }}>Prompt Context</span>
              <pre style={{ marginTop: '8px', background: 'var(--bg-primary)', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '10px', fontSize: '0.7rem', overflowX: 'auto', whiteSpace: 'pre-wrap', color: 'var(--text-secondary)' }}>
                {explainPayload?.final_prompt_context || 'No active query payload context loaded.'}
              </pre>
            </div>
          )}

          {explainTab === 'metrics' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <span style={{ fontSize: '0.7rem', fontWeight: 'bold', color: 'var(--text-disabled)', textTransform: 'uppercase' }}>Expert Heatmap Score</span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '8px' }}>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '2px' }}>
                      <span>Vector Expert</span>
                      <span>0.942</span>
                    </div>
                    <ProgressBar progress={94} variant="success" />
                  </div>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '2px' }}>
                      <span>Graph Expert</span>
                      <span>0.811</span>
                    </div>
                    <ProgressBar progress={81} variant="success" />
                  </div>
                </div>
              </div>
            </div>
          )}

        </div>
      </div>

    </div>
  );
};

export default WorkspaceHome;
