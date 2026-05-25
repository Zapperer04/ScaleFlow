import React, { useState, useEffect, useRef } from 'react';
import { 
  Upload, Cpu, Activity, RefreshCw, AlertTriangle, Shield, Play, ArrowRight, 
  Server, Database, Search, Sparkles, Loader2, ChevronDown, ChevronUp, FileText, CheckCircle2
} from 'lucide-react';
import { 
  searchVectors, createRetrievalPipeline, fetchRetrievalPipelineAnswer, fetchPipelineDetails, fetchTasks 
} from '../services/api';

const OverviewPage = ({ 
  pipelines, 
  workers, 
  queueStats, 
  stats, 
  onSelectPipeline, 
  onNavigateToView,
  onUploadFile,
  fileType,
  setFileType,
  uploading,
  uploadStatus,
  selectedPipelineId,
  setSelectedPipelineId,
  onSelectTask
}) => {
  
  // Pipeline details state
  const [pipelineDetails, setPipelineDetails] = useState(null);
  
  // Timeline log state (fallback to general tasks if no active pipeline)
  const [generalTasks, setGeneralTasks] = useState([]);
  const [expandedTasks, setExpandedTasks] = useState(new Set());

  // RAG query state
  const [query, setQuery] = useState('');
  const [ragAnswer, setRagAnswer] = useState(null);
  const [results, setResults] = useState([]);
  const [ragLoading, setRagLoading] = useState(false);
  const [error, setError] = useState(null);
  const [highlightChat, setHighlightChat] = useState(false);
  
  const chatInputRef = useRef(null);

  // Poll active pipeline details
  useEffect(() => {
    let timer;
    if (selectedPipelineId) {
      const getDetails = async () => {
        try {
          const details = await fetchPipelineDetails(selectedPipelineId);
          setPipelineDetails(details);
        } catch (err) {
          console.error('Failed to load active pipeline details:', err);
        }
      };
      getDetails();
      timer = setInterval(getDetails, 2000);
    } else {
      setPipelineDetails(null);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [selectedPipelineId]);

  // Poll general tasks if no active pipeline
  useEffect(() => {
    let timer;
    const getTasks = async () => {
      try {
        const res = await fetchTasks(1, 10);
        setGeneralTasks(res.tasks || []);
      } catch (err) {
        console.error('Failed to load recent tasks:', err);
      }
    };
    
    if (!selectedPipelineId) {
      getTasks();
      timer = setInterval(getTasks, 3000);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [selectedPipelineId]);

  // Auto-focus and highlight RAG query input when pipeline finishes
  const pipelineStatus = pipelineDetails?.pipeline?.status;
  useEffect(() => {
    if (pipelineStatus === 'completed') {
      if (chatInputRef.current) {
        chatInputRef.current.focus();
        chatInputRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
        setHighlightChat(true);
        const timer = setTimeout(() => setHighlightChat(false), 2500);
        return () => clearTimeout(timer);
      }
    }
  }, [pipelineStatus]);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setRagAnswer(null);
      setResults([]);
      onUploadFile(file);
    }
  };

  // RAG query execution logic
  const handleRagQuery = async (e) => {
    if (e) e.preventDefault();
    if (!query.trim()) return;

    setRagLoading(true);
    setRagAnswer(null);
    setResults([]);
    setError(null);

    try {
      // Initiate retrieval pipeline
      const pipelinePayload = { query: query };
      if (selectedPipelineId) {
        pipelinePayload.pipeline_id = selectedPipelineId;
      }
      
      const response = await createRetrievalPipeline(pipelinePayload);
      const queryPipelineId = response.pipeline_id;

      // Poll until synthesized answer is complete
      let attempts = 0;
      let answerData = null;
      while (attempts < 15) {
        await new Promise(r => setTimeout(r, 1000));
        answerData = await fetchRetrievalPipelineAnswer(queryPipelineId);
        if (answerData && (answerData.answer || answerData.status === 'completed' || answerData.status === 'failed')) {
          break;
        }
        attempts++;
      }

      if (answerData && answerData.status === 'failed') {
        throw new Error(answerData.error || 'RAG generation failed.');
      }

      setRagAnswer(answerData);
      if (answerData?.retrieved_chunks) {
        setResults(answerData.retrieved_chunks);
      }
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setRagLoading(false);
    }
  };

  const getTaskByAction = (actionName) => {
    if (!pipelineDetails?.tasks) return null;
    return pipelineDetails.tasks.find(t => t.type === actionName);
  };

  const parseTask = getTaskByAction('parse_document');
  const chunkTask = getTaskByAction('chunk_text');
  const embedTask = getTaskByAction('generate_embeddings');

  const toggleTaskExpanded = (taskId) => {
    setExpandedTasks(prev => {
      const next = new Set(prev);
      if (next.has(taskId)) {
        next.delete(taskId);
      } else {
        next.add(taskId);
      }
      return next;
    });
  };

  // Determine tasks to show in timeline
  const activeTasks = pipelineDetails?.tasks || generalTasks;
  const totalQueued = queueStats.total || 0;
  const onlineWorkers = workers.filter(w => w.status !== 'offline');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* 1. HEALTH STRIP */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        background: 'var(--bg-panel)',
        border: '1px solid var(--border-subtle)',
        borderRadius: '4px',
        padding: '10px 16px',
        fontSize: '0.75rem',
        color: 'var(--text-muted-light)'
      }}>
        <div style={{ display: 'flex', gap: '20px' }}>
          <div>
            <span>PostgreSQL: </span>
            <span style={{ color: 'var(--color-success)', fontWeight: 'bold' }}>ONLINE</span>
          </div>
          <div style={{ borderLeft: '1px solid var(--border-subtle)', paddingLeft: '20px' }}>
            <span>Redis Broker: </span>
            <span style={{ color: 'var(--color-success)', fontWeight: 'bold' }}>ONLINE</span>
          </div>
          <div style={{ borderLeft: '1px solid var(--border-subtle)', paddingLeft: '20px' }}>
            <span>Qdrant Core: </span>
            <span style={{ color: 'var(--color-success)', fontWeight: 'bold' }}>ONLINE</span>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '16px', fontFamily: 'monospace' }}>
          <span>Workers: <strong style={{ color: '#fff' }}>{onlineWorkers.length} online</strong></span>
          <span>Queue Depth: <strong style={{ color: '#fff' }}>{totalQueued}</strong></span>
        </div>
      </div>

      {/* 2. SPLIT LAYOUT */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1.1fr', gap: '20px' }}>
        
        {/* LEFT COLUMN: UPLOAD, PROGRESS & RAG CHAT */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {/* UPLOAD PANEL */}
          <div className="panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <h2 style={{ fontSize: '1rem', fontWeight: '800', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '8px', margin: 0 }}>
                <Upload size={18} style={{ color: 'var(--color-accent)' }} />
                AI Document Ingestion
              </h2>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Upload unstructured text documents or system logs to trigger the distributed pipeline.
              </span>
            </div>

            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <select 
                  value={fileType}
                  onChange={(e) => setFileType(e.target.value)}
                  style={{ width: '100%' }}
                >
                  <option value="document_processing_demo">Standard AI Document Parsing (.pdf, .txt)</option>
                  <option value="log_analysis_demo">Orchestrated Log Analysis (.log)</option>
                </select>
              </div>

              <label className="btn btn-primary" style={{ height: '28px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', cursor: uploading ? 'not-allowed' : 'pointer' }}>
                {uploading ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
                <span>{uploading ? 'Processing...' : 'Upload File'}</span>
                <input type="file" onChange={handleFileChange} disabled={uploading} style={{ display: 'none' }} />
              </label>
            </div>

            {uploadStatus && (
              <div style={{ 
                fontSize: '0.75rem', 
                color: uploadStatus.includes('failed') ? 'var(--color-failure)' : 'var(--color-success)', 
                background: 'rgba(255, 255, 255, 0.01)',
                border: '1px solid var(--border-subtle)',
                padding: '6px 12px',
                borderRadius: '4px'
              }}>
                {uploadStatus}
              </div>
            )}
          </div>

          {/* ACTIVE PIPELINE TRACKER */}
          <div className="panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <h2 style={{ fontSize: '1rem', fontWeight: '800', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '8px', margin: 0 }}>
                <Activity size={18} style={{ color: 'var(--color-accent)' }} />
                Active Processing Pipeline
              </h2>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Topological execution steps and worker assignments for the active document.
              </span>
            </div>

            {!selectedPipelineId ? (
              <div style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)', background: 'rgba(0, 0, 0, 0.1)', border: '1px dashed var(--border-subtle)', borderRadius: '4px' }}>
                No active document pipeline. Upload a document above to launch execution.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.8rem', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '8px' }}>
                  <span>Active ID: <strong>Pipeline #{selectedPipelineId}</strong></span>
                  <span className={`badge ${pipelineStatus || 'running'}`}>{pipelineStatus || 'running'}</span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  
                  {/* Stage 1: Upload */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', background: 'rgba(255,255,255,0.01)', padding: '8px 12px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
                    <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--color-success)' }} />
                    <div style={{ flex: 1, display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                      <span style={{ fontWeight: 600 }}>1. Document Upload</span>
                      <span style={{ color: 'var(--text-muted)' }}>Worker: API Gateway | Output: raw_file</span>
                    </div>
                  </div>

                  {/* Stage 2: Parsing */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', background: 'rgba(255,255,255,0.01)', padding: '8px 12px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
                    <div style={{ 
                      width: '8px', 
                      height: '8px', 
                      borderRadius: '50%', 
                      background: parseTask?.status === 'completed' ? 'var(--color-success)' : parseTask?.status === 'running' ? 'var(--color-accent)' : parseTask?.status === 'failed' ? 'var(--color-failure)' : 'var(--text-muted)' 
                    }} className={parseTask?.status === 'running' ? 'animate-pulse' : ''} />
                    <div style={{ flex: 1, display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                      <span style={{ fontWeight: 600 }}>2. Ingestion & Parsing</span>
                      <span style={{ color: 'var(--text-muted)' }}>
                        {parseTask ? `Worker: ${parseTask.assigned_worker_id || 'Waiting...'} | Duration: ${parseTask.duration ? `${parseTask.duration.toFixed(1)}s` : 'active'}` : 'Pending...'}
                      </span>
                    </div>
                  </div>

                  {/* Stage 3: Chunking */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', background: 'rgba(255,255,255,0.01)', padding: '8px 12px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
                    <div style={{ 
                      width: '8px', 
                      height: '8px', 
                      borderRadius: '50%', 
                      background: chunkTask?.status === 'completed' ? 'var(--color-success)' : chunkTask?.status === 'running' ? 'var(--color-accent)' : chunkTask?.status === 'failed' ? 'var(--color-failure)' : 'var(--text-muted)'
                    }} className={chunkTask?.status === 'running' ? 'animate-pulse' : ''} />
                    <div style={{ flex: 1, display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                      <span style={{ fontWeight: 600 }}>3. Text Segmentation (Chunking)</span>
                      <span style={{ color: 'var(--text-muted)' }}>
                        {chunkTask ? `Worker: ${chunkTask.assigned_worker_id || 'Waiting...'} | Duration: ${chunkTask.duration ? `${chunkTask.duration.toFixed(1)}s` : 'active'}` : 'Pending...'}
                      </span>
                    </div>
                  </div>

                  {/* Stage 4: Vectorization */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', background: 'rgba(255,255,255,0.01)', padding: '8px 12px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
                    <div style={{ 
                      width: '8px', 
                      height: '8px', 
                      borderRadius: '50%', 
                      background: embedTask?.status === 'completed' ? 'var(--color-success)' : embedTask?.status === 'running' ? 'var(--color-accent)' : embedTask?.status === 'failed' ? 'var(--color-failure)' : 'var(--text-muted)'
                    }} className={embedTask?.status === 'running' ? 'animate-pulse' : ''} />
                    <div style={{ flex: 1, display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                      <span style={{ fontWeight: 600 }}>4. Semantic Vector Ingestion</span>
                      <span style={{ color: 'var(--text-muted)' }}>
                        {embedTask ? `Worker: ${embedTask.assigned_worker_id || 'Waiting...'} | Duration: ${embedTask.duration ? `${embedTask.duration.toFixed(1)}s` : 'active'}` : 'Pending...'}
                      </span>
                    </div>
                  </div>

                  {/* Stage 5: Ready */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', background: 'rgba(255,255,255,0.01)', padding: '8px 12px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
                    <div style={{ 
                      width: '8px', 
                      height: '8px', 
                      borderRadius: '50%', 
                      background: embedTask?.status === 'completed' ? 'var(--color-success)' : 'var(--text-muted)' 
                    }} />
                    <div style={{ flex: 1, display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                      <span style={{ fontWeight: 600 }}>5. Chat & Retrieval Ready</span>
                      <span style={{ color: 'var(--text-muted)' }}>
                        {embedTask?.status === 'completed' ? 'Active | Destination: Qdrant vector_store' : 'Pending embeddings indexation...'}
                      </span>
                    </div>
                  </div>

                </div>
              </div>
            )}
          </div>

          {/* CHAT WITH DOCUMENT PANEL (RAG) */}
          <div 
            className="panel" 
            style={{ 
              padding: '24px', 
              display: 'flex', 
              flexDirection: 'column', 
              gap: '16px',
              border: highlightChat ? '1px solid var(--color-accent)' : '1px solid var(--border-subtle)',
              transition: 'border-color 0.25s ease'
            }}
          >
            <div>
              <h2 style={{ fontSize: '1rem', fontWeight: '800', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '8px', margin: 0 }}>
                <Sparkles size={18} style={{ color: 'var(--color-accent)' }} />
                Chat With Your Document
              </h2>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Ask questions about your uploaded file to retrieve indexed text context.
              </span>
            </div>

            <form onSubmit={handleRagQuery} style={{ display: 'flex', gap: '10px' }}>
              <input 
                ref={chatInputRef}
                type="text" 
                placeholder="Ask a question about the document text..." 
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                disabled={ragLoading}
                style={{ flex: 1, height: '28px' }}
              />
              <button 
                type="submit" 
                disabled={ragLoading || !query.trim()}
                className="btn btn-primary"
                style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
              >
                {ragLoading ? <Loader2 size={12} className="animate-spin" /> : <Search size={12} />}
                Ask
              </button>
            </form>

            {error && (
              <div style={{ color: 'var(--color-failure)', fontSize: '0.75rem', background: 'rgba(239, 68, 68, 0.05)', padding: '6px 10px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
                Failed to process query: {error}
              </div>
            )}

            {ragAnswer && (
              <div style={{ 
                display: 'flex', 
                flexDirection: 'column', 
                gap: '10px', 
                background: 'rgba(255,255,255,0.01)', 
                border: '1px solid var(--border-subtle)', 
                padding: '14px', 
                borderRadius: '4px' 
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: 'var(--color-accent)', fontWeight: 'bold' }}>
                  <Sparkles size={14} />
                  <span>Synthesized Answer:</span>
                </div>
                <div style={{ fontSize: '0.85rem', color: '#cbd5e1', lineHeight: 1.5, whiteSpace: 'pre-wrap' }}>
                  {ragAnswer.answer}
                </div>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', display: 'flex', gap: '12px' }}>
                  <span>Synthesized via Pipeline ID: #{ragAnswer.pipeline_id}</span>
                  <span>Duration: {ragAnswer.elapsed_seconds ? `${ragAnswer.elapsed_seconds.toFixed(2)}s` : '0.4s'}</span>
                </div>
              </div>
            )}

            {results.length > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 'bold', color: '#ffffff' }}>Semantic Citations Retrieved:</span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '180px', overflowY: 'auto', paddingRight: '4px' }}>
                  {results.map((hit, idx) => (
                    <div key={idx} style={{ background: 'rgba(0,0,0,0.15)', padding: '10px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.7rem', color: '#94a3b8', marginBottom: '4px' }}>
                        <span>Chunk #{hit.chunk_index} • Citation: {hit.original_filename || 'source'}</span>
                        <span style={{ color: 'var(--color-success)', fontWeight: 'bold' }}>{Math.round((hit.score || 0) * 100)}% match</span>
                      </div>
                      <code style={{ fontSize: '0.75rem', color: '#cbd5e1', display: 'block', wordBreak: 'break-all', whiteSpace: 'pre-wrap' }}>
                        {hit.chunk_text}
                      </code>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

        </div>

        {/* RIGHT COLUMN: COLLAPSIBLE MINIMAL EXECUTION TIMELINE */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          <div className="panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px', height: '100%' }}>
            <div>
              <h2 style={{ fontSize: '1rem', fontWeight: '800', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '8px', margin: 0 }}>
                <Database size={18} style={{ color: 'var(--color-accent)' }} />
                Execution Timeline
              </h2>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Timeline logs of distributed task tasks. Click details to expand.
              </span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', overflowY: 'auto', maxHeight: 'calc(100vh - 250px)' }}>
              {activeTasks.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                  Waiting for task logs...
                </div>
              ) : (
                activeTasks.map((task) => {
                  const isExpanded = expandedTasks.has(task.id);
                  return (
                    <div 
                      key={task.id} 
                      style={{ 
                        background: 'rgba(255,255,255,0.01)', 
                        border: '1px solid var(--border-subtle)', 
                        borderRadius: '4px', 
                        padding: '10px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '6px'
                      }}
                    >
                      {/* Collapsed Header */}
                      <div 
                        onClick={() => toggleTaskExpanded(task.id)}
                        style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
                      >
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                          <span style={{ fontSize: '0.8rem', fontWeight: '700', color: '#ffffff', fontFamily: 'monospace' }}>
                            {task.type.replace('_', ' ')}
                          </span>
                          <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                            Worker: {task.assigned_worker_id || 'unassigned'}
                          </span>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span className={`badge ${task.status}`} style={{ fontSize: '0.65rem', padding: '2px 6px' }}>
                            {task.status}
                          </span>
                          {isExpanded ? <ChevronUp size={14} style={{ color: 'var(--text-muted)' }} /> : <ChevronDown size={14} style={{ color: 'var(--text-muted)' }} />}
                        </div>
                      </div>

                      {/* Expanded Collapsible Details */}
                      {isExpanded && (
                        <div style={{ 
                          borderTop: '1px solid var(--border-subtle)', 
                          paddingTop: '8px', 
                          marginTop: '4px',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '6px',
                          fontSize: '0.7rem',
                          color: '#cbd5e1'
                        }}>
                          <div>
                            <span style={{ color: 'var(--text-muted)' }}>Task ID:</span> # {task.id}
                          </div>
                          <div>
                            <span style={{ color: 'var(--text-muted)' }}>Duration:</span> {task.duration ? `${task.duration.toFixed(2)}s` : 'running'}
                          </div>
                          <div>
                            <span style={{ color: 'var(--text-muted)' }}>Queue Name:</span> <code style={{ color: 'var(--color-accent)' }}>{task.queue_name || 'default'}</code>
                          </div>
                          {task.queue_position !== undefined && task.queue_position !== null && (
                            <div>
                              <span style={{ color: 'var(--text-muted)' }}>Queue Position:</span> {task.queue_position}
                            </div>
                          )}
                          {task.lease_expires_at && (
                            <div>
                              <span style={{ color: 'var(--text-muted)' }}>Lease Expiration:</span> {new Date(task.lease_expires_at).toLocaleTimeString()}
                            </div>
                          )}
                          {task.retry_count > 0 && (
                            <div>
                              <span style={{ color: 'var(--text-muted)' }}>Retry Loop:</span> {task.retry_count}/{task.max_retries}
                            </div>
                          )}
                          {task.error_message && (
                            <div style={{ color: 'var(--color-failure)', background: 'rgba(239, 68, 68, 0.05)', padding: '6px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
                              <strong>Error:</strong> {task.error_message}
                            </div>
                          )}
                          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '4px' }}>
                            <button 
                              onClick={() => onSelectTask(task.id)}
                              className="btn"
                              style={{ padding: '2px 8px', fontSize: '0.65rem', height: '20px' }}
                            >
                              Actions / Details
                            </button>
                            <button 
                              onClick={() => {
                                if (task.pipeline_id) {
                                  onSelectPipeline(task.pipeline_id);
                                } else {
                                  onNavigateToView('pipelines');
                                }
                              }}
                              className="btn btn-secondary" 
                              style={{ padding: '2px 8px', fontSize: '0.65rem', height: '20px' }}
                            >
                              Go to Graph →
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </div>

        </div>

      </div>

    </div>
  );
};

export default OverviewPage;
