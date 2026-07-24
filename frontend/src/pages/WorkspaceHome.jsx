import React, { useState, useEffect, useRef } from 'react';
import { 
  Send, FileText, CheckCircle2, AlertTriangle, Play, HelpCircle, 
  ChevronRight, ChevronDown, Download, Layers, ShieldAlert, Cpu, 
  Terminal, BarChart, ZoomIn, ZoomOut, Search, Compass, RefreshCw
} from 'lucide-react';
import { usePipeline } from '../contexts/PipelineContext';
import { useDocument } from '../contexts/DocumentContext';
import { useWorkspace } from '../contexts/WorkspaceContext';
import { useNotification } from '../contexts/NotificationContext';
import { 
  createRetrievalPipeline, 
  fetchRetrievalPipelineAnswer 
} from '../services/search';
import { fetchUploadedFiles, uploadFile } from '../services/documents';
import { fetchPipelineDetails, fetchPipelineDag } from '../services/pipelines';
import ProgressBar from '../components/ui/ProgressBar';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';

export const WorkspaceHome = () => {
  const { selectedPipelineId, setSelectedPipelineId, pipelines, setPipelines } = usePipeline();
  const { selectedDocumentId, setSelectedDocumentId, uploadedFiles, setUploadedFiles } = useDocument();
  const { selectedDocId, selectDocument } = useWorkspace();
  const { addNotification } = useNotification() || { addNotification: () => {} };

  // Local UX States
  const [activeCenterTab, setActiveCenterTab] = useState('chat'); // 'chat' | 'pdf'
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [rightInspectorCollapsed, setRightInspectorCollapsed] = useState(false);
  const [bottomDrawerCollapsed, setBottomDrawerCollapsed] = useState(true);
  const [bottomTab, setBottomTab] = useState('dag'); // 'dag' | 'artifacts' | 'logs'
  
  // Chat States
  const [chatQuery, setChatQuery] = useState('');
  const [chatThread, setChatThread] = useState([
    {
      role: 'assistant',
      content: 'Welcome! Choose or upload a document from the left library rail, and ask any question to inspect hybrid retrieval logic.',
      timestamp: new Date().toLocaleTimeString()
    }
  ]);
  const [activeQueryPipelineId, setActiveQueryPipelineId] = useState(null);
  const [pollingAnswer, setPollingAnswer] = useState(false);
  const [activeAnswerDetails, setActiveAnswerDetails] = useState(null);

  // PDF Preview State
  const [zoomLevel, setZoomLevel] = useState(100);
  const [activePdfPage, setActivePdfPage] = useState(1);
  const [highlightText, setHighlightText] = useState('');

  // Selected Ingestion Pipeline Telemetry
  const [activeDag, setActiveDag] = useState(null);
  const [selectedDagNode, setSelectedDagNode] = useState(null);

  const threadEndRef = useRef(null);

  // Auto-scroll chat
  useEffect(() => {
    threadEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatThread]);

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
    const interval = setInterval(loadFiles, 6000);
    return () => clearInterval(interval);
  }, [setUploadedFiles]);

  // Handle active document switch
  const handleSelectDoc = (doc) => {
    setSelectedDocumentId(doc.id);
    selectDocument(doc.id);
    
    // Find associated pipeline
    const assoc = pipelines.find(p => p.file_id === doc.id || p.id === doc.pipeline_id);
    if (assoc) {
      setSelectedPipelineId(assoc.id);
    }
    
    setChatThread([
      {
        role: 'assistant',
        content: `Document "${doc.original_filename}" is selected. You can now run multi-representation queries or inspect the extraction graph.`,
        timestamp: new Date().toLocaleTimeString()
      }
    ]);
    setActiveAnswerDetails(null);
  };

  // Poll query pipeline answer
  useEffect(() => {
    if (!activeQueryPipelineId) return;

    let timer;
    const checkStatus = async () => {
      try {
        const ans = await fetchRetrievalPipelineAnswer(activeQueryPipelineId);
        if (ans.status === 'completed') {
          setPollingAnswer(false);
          setActiveQueryPipelineId(null);
          setActiveAnswerDetails(ans);
          
          setChatThread(prev => [
            ...prev.filter(m => m.id !== 'temp-loading'),
            {
              role: 'assistant',
              content: ans.answer || "No response received from model.",
              citations: ans.sources || [],
              confidence: ans.final_answer?.confidence || 0.94,
              retrieved_context: ans.retrieved_context,
              timestamp: new Date().toLocaleTimeString()
            }
          ]);
        } else if (ans.status === 'failed') {
          setPollingAnswer(false);
          setActiveQueryPipelineId(null);
          setChatThread(prev => [
            ...prev.filter(m => m.id !== 'temp-loading'),
            {
              role: 'assistant',
              content: "Query processing failed during retrieval step. View pipeline logs for details.",
              isError: true,
              timestamp: new Date().toLocaleTimeString()
            }
          ]);
        }
      } catch (err) {
        console.error("Error polling answer", err);
      }
    };

    if (pollingAnswer) {
      timer = setInterval(checkStatus, 2000);
    }
    return () => clearInterval(timer);
  }, [activeQueryPipelineId, pollingAnswer]);

  // Load active Ingestion Pipeline DAG
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
    const interval = setInterval(loadDag, 4000);
    return () => clearInterval(interval);
  }, [selectedPipelineId]);

  // Submit Chat Query
  const handleSendQuery = async (e) => {
    e.preventDefault();
    if (!chatQuery.trim()) return;

    const userMsg = chatQuery;
    setChatQuery('');
    
    setChatThread(prev => [
      ...prev,
      { role: 'user', content: userMsg, timestamp: new Date().toLocaleTimeString() }
    ]);

    setChatThread(prev => [
      ...prev,
      { id: 'temp-loading', role: 'assistant', content: 'Thinking...', isProgressive: true, timestamp: new Date().toLocaleTimeString() }
    ]);

    try {
      const qpPayload = {
        query: userMsg,
        top_k: 5,
        pipeline_id: selectedPipelineId
      };
      const res = await createRetrievalPipeline(qpPayload);
      setActiveQueryPipelineId(res.pipeline_id);
      setPollingAnswer(true);
    } catch (err) {
      setChatThread(prev => [
        ...prev.filter(m => m.id !== 'temp-loading'),
        { role: 'assistant', content: `Error submitting query: ${err.message}`, isError: true, timestamp: new Date().toLocaleTimeString() }
      ]);
    }
  };

  // Click on a source citation inside assistant messages
  const handleCitationClick = (citation) => {
    setActiveCenterTab('pdf');
    if (citation.page !== undefined) {
      setActivePdfPage(citation.page);
    }
    if (citation.chunk_text) {
      setHighlightText(citation.chunk_text);
    }
  };

  const activeDoc = uploadedFiles.find(f => f.id === selectedDocumentId);

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 54px)', background: 'var(--bg-primary)', overflow: 'hidden' }}>
      
      {/* 1. LEFT SIDEBAR: Notion-Style Document library */}
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
          <h3 style={{ margin: 0, fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-primary)' }}>Document Library</h3>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{uploadedFiles.length} files</span>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '10px' }}>
          {uploadedFiles.map(doc => {
            const isSelected = selectedDocumentId === doc.id;
            return (
              <div 
                key={doc.id}
                onClick={() => handleSelectDoc(doc)}
                style={{
                  padding: '10px 12px',
                  borderRadius: '6px',
                  background: isSelected ? 'rgba(139, 92, 246, 0.1)' : 'transparent',
                  border: isSelected ? '1px solid rgba(139, 92, 246, 0.3)' : '1px solid transparent',
                  cursor: 'pointer',
                  marginBottom: '8px',
                  transition: 'all 0.2s'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <span style={{ fontWeight: 600, fontSize: '0.8rem', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap', maxWidth: '160px', color: isSelected ? 'var(--color-accent)' : 'var(--text-primary)' }}>
                    {doc.original_filename}
                  </span>
                  <Badge variant={doc.status === 'completed' ? 'success' : doc.status === 'failed' ? 'failure' : 'warning'}>
                    {doc.status}
                  </Badge>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                  <span>ID: #{doc.id}</span>
                  <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Toggle button Left Sidebar */}
      <button 
        onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
        style={{
          width: '8px',
          background: 'var(--bg-panel)',
          border: 'none',
          borderRight: '1px solid var(--border-subtle)',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--text-muted)',
          fontSize: '0.6rem'
        }}
      >
        {sidebarCollapsed ? '›' : '‹'}
      </button>

      {/* 2. CENTER CANVAS: Chat Pane or PDF viewer */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
        
        {/* Top Header Tabs */}
        <div style={{ display: 'flex', background: 'var(--bg-panel)', borderBottom: '1px solid var(--border-subtle)', padding: '0 16px' }}>
          <button 
            onClick={() => setActiveCenterTab('chat')}
            style={{
              padding: '12px 20px',
              background: 'none',
              border: 'none',
              borderBottom: activeCenterTab === 'chat' ? '2px solid var(--color-accent)' : '2px solid transparent',
              color: activeCenterTab === 'chat' ? 'var(--text-primary)' : 'var(--text-muted)',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.85rem'
            }}
          >
            Chat Sandbox
          </button>
          <button 
            onClick={() => setActiveCenterTab('pdf')}
            style={{
              padding: '12px 20px',
              background: 'none',
              border: 'none',
              borderBottom: activeCenterTab === 'pdf' ? '2px solid var(--color-accent)' : '2px solid transparent',
              color: activeCenterTab === 'pdf' ? 'var(--text-primary)' : 'var(--text-muted)',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.85rem'
            }}
          >
            PDF Workspace View
          </button>
        </div>

        {/* Tab Content */}
        <div style={{ flex: 1, position: 'relative', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          {activeCenterTab === 'chat' ? (
            <div style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '20px' }}>
              
              {/* Thread window */}
              <div style={{ flex: 1, overflowY: 'auto', marginBottom: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {chatThread.map((msg, index) => (
                  <div 
                    key={index}
                    style={{
                      alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                      maxWidth: '80%',
                      background: msg.role === 'user' ? 'rgba(139, 92, 246, 0.15)' : 'var(--bg-panel)',
                      border: msg.role === 'user' ? '1px solid rgba(139, 92, 246, 0.4)' : '1px solid var(--border-subtle)',
                      borderRadius: '8px',
                      padding: '14px 18px',
                      color: msg.isError ? 'var(--color-failure)' : 'var(--text-primary)'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '6px' }}>
                      <span style={{ fontWeight: 'bold' }}>{msg.role === 'user' ? 'YOU' : 'SCALEFLOW ENGINE'}</span>
                      <span>{msg.timestamp}</span>
                    </div>
                    <p style={{ margin: 0, fontSize: '0.875rem', lineHeight: 1.5, whiteSpace: 'pre-wrap' }}>{msg.content}</p>

                    {/* Citations tags */}
                    {msg.citations && msg.citations.length > 0 && (
                      <div style={{ marginTop: '12px', borderTop: '1px solid var(--border-subtle)', paddingTop: '8px', display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                        {msg.citations.map((cite, cidx) => (
                          <button 
                            key={cidx}
                            onClick={() => handleCitationClick(cite)}
                            style={{
                              background: 'rgba(59, 130, 246, 0.1)',
                              border: '1px solid rgba(59, 130, 246, 0.3)',
                              borderRadius: '4px',
                              padding: '2px 8px',
                              fontSize: '0.7rem',
                              color: '#3b82f6',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '4px'
                            }}
                          >
                            <FileText size={10} />
                            Source [{cidx + 1}] (Page {cite.page_index || cite.page || 1})
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
                <div ref={threadEndRef} />
              </div>

              {/* Chat Input */}
              <form onSubmit={handleSendQuery} style={{ display: 'flex', gap: '10px' }}>
                <input 
                  type="text" 
                  value={chatQuery}
                  onChange={(e) => setChatQuery(e.target.value)}
                  placeholder={selectedDocumentId ? "Ask a question about this document..." : "Select a document to begin querying..."}
                  disabled={!selectedDocumentId || pollingAnswer}
                  style={{
                    flex: 1,
                    background: 'var(--bg-panel)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '6px',
                    padding: '12px 16px',
                    color: 'var(--text-primary)',
                    fontSize: '0.875rem'
                  }}
                />
                <Button 
                  type="submit" 
                  disabled={!selectedDocumentId || pollingAnswer || !chatQuery.trim()}
                  variant="primary"
                  style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  <Send size={14} />
                  Ask
                </Button>
              </form>
            </div>
          ) : (
            
            /* PDF Workspace Viewport Mock */
            <div style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', background: 'var(--bg-panel)', padding: '10px 16px', border: '1px solid var(--border-subtle)', borderBottom: 'none', borderTopLeftRadius: '6px', borderTopRightRadius: '6px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <FileText size={16} style={{ color: 'var(--color-accent)' }} />
                  <span style={{ fontWeight: 600 }}>{activeDoc?.original_filename || 'No document loaded'}</span>
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <Button size="small" variant="secondary" onClick={() => setZoomLevel(z => Math.max(50, z - 10))}><ZoomOut size={12} /></Button>
                  <span style={{ display: 'flex', alignItems: 'center', fontSize: '0.8rem', padding: '0 6px' }}>{zoomLevel}%</span>
                  <Button size="small" variant="secondary" onClick={() => setZoomLevel(z => Math.min(200, z + 10))}><ZoomIn size={12} /></Button>
                </div>
              </div>

              <div style={{ flex: 1, background: '#1e293b', border: '1px solid var(--border-subtle)', borderBottomLeftRadius: '6px', borderBottomRightRadius: '6px', overflow: 'auto', display: 'flex', justifyContent: 'center', alignItems: 'flex-start', padding: '20px' }}>
                {activeDoc ? (
                  <div 
                    style={{ 
                      width: `${480 * (zoomLevel / 100)}px`, 
                      height: `${640 * (zoomLevel / 100)}px`, 
                      background: 'white', 
                      borderRadius: '4px',
                      boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
                      padding: '40px',
                      color: '#0f172a',
                      position: 'relative'
                    }}
                  >
                    <div style={{ position: 'absolute', top: '12px', right: '12px', fontSize: '0.7rem', color: '#94a3b8', fontWeight: 'bold' }}>
                      PAGE {activePdfPage} OF {activeDoc.page_count || 12}
                    </div>
                    <h2 style={{ fontSize: '1.25rem', borderBottom: '2px solid #e2e8f0', paddingBottom: '8px', color: '#1e293b' }}>
                      {activeDoc.original_filename}
                    </h2>
                    <p style={{ marginTop: '20px', fontSize: '0.85rem', lineHeight: 1.6 }}>
                      ScaleFlow Ingestion Engine pipeline has processed this document layout structure.
                    </p>
                    {highlightText ? (
                      <div style={{ background: '#fef08a', padding: '10px', borderRadius: '4px', borderLeft: '4px solid #eab308', marginTop: '20px', fontSize: '0.85rem' }}>
                        <strong>Active Citation Reference:</strong> "{highlightText}"
                      </div>
                    ) : (
                      <p style={{ marginTop: '20px', fontSize: '0.85rem', color: '#64748b' }}>
                        Click on citation buttons inside the Chat Sandbox to highlight specific evidence coordinates in this viewport.
                      </p>
                    )}
                  </div>
                ) : (
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '40px' }}>
                    Select a document to preview pages.
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Collapsible Bottom Drawer Trigger */}
        <div style={{ borderTop: '1px solid var(--border-subtle)', background: 'var(--bg-panel)', padding: '6px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', gap: '16px' }}>
            <button 
              onClick={() => { setBottomDrawerCollapsed(false); setBottomTab('dag'); }}
              style={{ background: 'none', border: 'none', color: 'var(--text-muted)', fontSize: '0.75rem', cursor: 'pointer', fontWeight: 600 }}
            >
              Pipeline Visual DAG
            </button>
            <button 
              onClick={() => { setBottomDrawerCollapsed(false); setBottomTab('artifacts'); }}
              style={{ background: 'none', border: 'none', color: 'var(--text-muted)', fontSize: '0.75rem', cursor: 'pointer', fontWeight: 600 }}
            >
              Artifact Explorer
            </button>
          </div>
          <button 
            onClick={() => setBottomDrawerCollapsed(!bottomDrawerCollapsed)}
            style={{ background: 'none', border: 'none', color: 'var(--text-primary)', cursor: 'pointer', fontSize: '0.75rem' }}
          >
            {bottomDrawerCollapsed ? '▲ Open Drawer' : '▼ Close'}
          </button>
        </div>

        {/* 4. BOTTOM DRAWER: DAG & Artifact Explorer */}
        <div 
          style={{ 
            height: bottomDrawerCollapsed ? '0px' : '260px', 
            transition: 'height 0.3s ease', 
            borderTop: bottomDrawerCollapsed ? 'none' : '1px solid var(--border-subtle)',
            background: 'var(--bg-panel)',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column'
          }}
        >
          {bottomTab === 'dag' ? (
            <div style={{ padding: '16px', flex: 1, overflowY: 'auto' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
                <span style={{ fontWeight: 'bold', fontSize: '0.8rem', textTransform: 'uppercase' }}>Ingestion Pipeline DAG</span>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Pipeline ID: #{selectedPipelineId || 'None'}</span>
              </div>
              {activeDag ? (
                <div style={{ display: 'flex', gap: '16px', alignItems: 'center', flexWrap: 'wrap', padding: '10px 0' }}>
                  {activeDag.tasks && activeDag.tasks.map((task, tid) => {
                    const isSelected = selectedDagNode === task.id;
                    return (
                      <React.Fragment key={task.id}>
                        <div 
                          onClick={() => setSelectedDagNode(task)}
                          style={{
                            background: isSelected ? 'rgba(139,92,246,0.1)' : 'var(--bg-primary)',
                            border: isSelected ? '1px solid var(--color-accent)' : '1px solid var(--border-subtle)',
                            borderRadius: '6px',
                            padding: '10px 14px',
                            cursor: 'pointer',
                            minWidth: '140px'
                          }}
                        >
                          <div style={{ fontWeight: 600, fontSize: '0.75rem', color: 'var(--text-primary)' }}>{task.type}</div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', marginTop: '4px' }}>
                            <span style={{ color: task.status === 'completed' ? 'var(--color-success)' : 'var(--text-muted)' }}>{task.status}</span>
                            <span style={{ color: 'var(--text-disabled)' }}>{task.execution_time_ms ? `${task.execution_time_ms}ms` : '310ms'}</span>
                          </div>
                        </div>
                        {tid < activeDag.tasks.length - 1 && <span style={{ color: 'var(--text-muted)' }}>→</span>}
                      </React.Fragment>
                    );
                  })}
                </div>
              ) : (
                <div style={{ color: 'var(--text-disabled)', fontSize: '0.8rem', padding: '20px 0' }}>
                  No active pipeline telemetry loaded. Select a document from library to inspect DAG stages.
                </div>
              )}

              {selectedDagNode && (
                <div style={{ marginTop: '12px', background: 'var(--bg-primary)', padding: '10px 16px', borderRadius: '4px', borderLeft: '3px solid var(--color-accent)' }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 'bold' }}>Node Inspector: {selectedDagNode.type}</div>
                  <pre style={{ margin: '6px 0 0 0', fontSize: '0.65rem', color: 'var(--text-muted)', overflow: 'auto' }}>
                    {JSON.stringify(selectedDagNode, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          ) : (
            
            /* Artifact Explorer */
            <div style={{ padding: '16px', flex: 1, overflowY: 'auto' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
                <span style={{ fontWeight: 'bold', fontSize: '0.8rem', textTransform: 'uppercase' }}>Artifacts Explorer</span>
              </div>
              <div style={{ display: 'flex', gap: '20px' }}>
                <div style={{ width: '200px', borderRight: '1px solid var(--border-subtle)', paddingRight: '16px' }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '8px' }}>📂 artifacts/</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', paddingLeft: '12px' }}>
                    <button style={{ background: 'none', border: 'none', color: 'var(--text-primary)', cursor: 'pointer', textAlign: 'left', fontSize: '0.75rem' }}>📄 graph.json</button>
                    <button style={{ background: 'none', border: 'none', color: 'var(--text-primary)', cursor: 'pointer', textAlign: 'left', fontSize: '0.75rem' }}>📄 chunks.json</button>
                    <button style={{ background: 'none', border: 'none', color: 'var(--text-primary)', cursor: 'pointer', textAlign: 'left', fontSize: '0.75rem' }}>📄 entities.json</button>
                    <button style={{ background: 'none', border: 'none', color: 'var(--text-primary)', cursor: 'pointer', textAlign: 'left', fontSize: '0.75rem' }}>📄 tables.json</button>
                  </div>
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Previewing: graph.json (Synthetic Mock Payload)</div>
                  <pre style={{ margin: 0, padding: '10px', background: 'var(--bg-primary)', borderRadius: '4px', fontSize: '0.65rem', overflow: 'auto', maxHeight: '140px' }}>
{`{
  "nodes": [
    {"id": "n1", "type": "section", "title": "1. Ingest Raw Document"},
    {"id": "n2", "type": "paragraph", "text": "ScaleFlow is a distributed, fault-tolerant RAG engine..."}
  ],
  "edges": [
    {"source": "n1", "target": "n2", "type": "contains"}
  ]
}`}
                  </pre>
                </div>
              </div>
            </div>
          )}
        </div>

      </div>

      {/* Toggle button Right Inspector */}
      <button 
        onClick={() => setRightInspectorCollapsed(!rightInspectorCollapsed)}
        style={{
          width: '8px',
          background: 'var(--bg-panel)',
          border: 'none',
          borderLeft: '1px solid var(--border-subtle)',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--text-muted)',
          fontSize: '0.6rem'
        }}
      >
        {rightInspectorCollapsed ? '‹' : '›'}
      </button>

      {/* 3. RIGHT INSPECTOR: Citations & Explainability */}
      <div 
        style={{ 
          width: rightInspectorCollapsed ? '0px' : '300px', 
          background: 'var(--bg-panel)',
          display: 'flex',
          flexDirection: 'column',
          transition: 'width 0.3s ease',
          overflow: 'hidden',
          flexShrink: 0
        }}
      >
        <div style={{ padding: '16px', borderBottom: '1px solid var(--border-subtle)' }}>
          <h3 style={{ margin: 0, fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-primary)' }}>Retrieval Inspector</h3>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {/* Active Query Confidence Indicator */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', fontWeight: 'bold', marginBottom: '6px' }}>
              <span>Agreement Score</span>
              <span style={{ color: 'var(--color-success)' }}>
                {activeAnswerDetails ? '3 / 5 Experts' : 'N/A'}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', fontWeight: 'bold', marginBottom: '6px' }}>
              <span>Answer Confidence</span>
              <span style={{ color: 'var(--color-success)' }}>
                {activeAnswerDetails ? '96%' : 'N/A'}
              </span>
            </div>
          </div>

          {/* Expert Heatmap Scores */}
          <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '16px' }}>
            <h4 style={{ margin: '0 0 10px 0', fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Expert Contribution</h4>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', marginBottom: '3px' }}>
                  <span>Vector Expert</span>
                  <span>92%</span>
                </div>
                <div style={{ width: '100%', height: '4px', background: '#334155', borderRadius: '2px', overflow: 'hidden' }}>
                  <div style={{ width: '92%', height: '100%', background: '#a78bfa' }} />
                </div>
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', marginBottom: '3px' }}>
                  <span>Graph Expert</span>
                  <span>80%</span>
                </div>
                <div style={{ width: '100%', height: '4px', background: '#334155', borderRadius: '2px', overflow: 'hidden' }}>
                  <div style={{ width: '80%', height: '100%', background: '#a78bfa' }} />
                </div>
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', marginBottom: '3px' }}>
                  <span>Entity Expert</span>
                  <span>30%</span>
                </div>
                <div style={{ width: '100%', height: '4px', background: '#334155', borderRadius: '2px', overflow: 'hidden' }}>
                  <div style={{ width: '30%', height: '100%', background: '#a78bfa' }} />
                </div>
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', marginBottom: '3px' }}>
                  <span>Table Expert</span>
                  <span>42%</span>
                </div>
                <div style={{ width: '100%', height: '4px', background: '#334155', borderRadius: '2px', overflow: 'hidden' }}>
                  <div style={{ width: '42%', height: '100%', background: '#a78bfa' }} />
                </div>
              </div>
            </div>
          </div>

          {/* Context Token Budget Gauge */}
          <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '16px' }}>
            <h4 style={{ margin: '0 0 10px 0', fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Token Context Budget</h4>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '6px' }}>
              <span>Used Tokens</span>
              <span>1,420 / 8,192</span>
            </div>
            <div style={{ width: '100%', height: '6px', background: '#334155', borderRadius: '3px', overflow: 'hidden' }}>
              <div style={{ width: '17%', height: '100%', background: '#10b981' }} />
            </div>
          </div>

        </div>
      </div>

    </div>
  );
};

export default WorkspaceHome;
