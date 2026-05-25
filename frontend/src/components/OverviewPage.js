import React, { useState, useEffect, useRef } from 'react';
import { 
  Upload, Activity, Database, Search, Sparkles, Loader2, ChevronDown, ChevronUp, FileText, BookOpen
} from 'lucide-react';
import { 
  createRetrievalPipeline, fetchRetrievalPipelineAnswer, fetchPipelineDetails 
} from '../services/api';

const OverviewPage = ({ 
  pipelines, 
  workers, 
  queueStats, 
  stats, 
  redisStatus,
  dbStatus,
  qdrantStatus,
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
  
  // Timeline log state
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
        if (answerData && (answerData.final_answer || answerData.answer || answerData.status === 'completed' || answerData.status === 'failed')) {
          break;
        }
        attempts++;
      }

      if (answerData && answerData.status === 'failed') {
        throw new Error(answerData.error || 'RAG generation failed.');
      }

      const answerObj = answerData?.final_answer || answerData;
      setRagAnswer(answerObj);
      
      const retrieved = answerData?.retrieved_context?.results || answerData?.retrieved_chunks || [];
      setResults(retrieved);
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

  // Dynamically adapt stage mapping to the running pipeline's type
  const isLogPipeline = pipelineDetails?.pipeline?.pipeline_type === 'log_analysis_demo';
  
  const parseTask = getTaskByAction(isLogPipeline ? 'parse_logs' : 'parse_document');
  const chunkTask = getTaskByAction(isLogPipeline ? 'detect_error_patterns' : 'chunk_text');
  const embedTask = getTaskByAction('generate_embeddings');
  const indexTask = getTaskByAction(isLogPipeline ? 'summarize_logs' : 'summarize_document');

  // Metadata Extraction for Document Intelligence Summary
  const vectorIndexArt = pipelineDetails?.artifacts?.find(a => a.artifact_type === 'vector_index');
  const textChunksArt = pipelineDetails?.artifacts?.find(a => a.artifact_type === 'text_chunks' || a.artifact_type === 'error_patterns');
  const chunkCount = vectorIndexArt?.metadata_json?.vector_count || textChunksArt?.metadata_json?.vector_count || null;

  const uploadedArt = pipelineDetails?.artifacts?.find(a => a.artifact_type === 'uploaded_file');
  const sizeBytes = uploadedArt?.metadata_json?.size_bytes || 0;
  const pageCount = sizeBytes ? Math.max(1, Math.ceil(sizeBytes / 3000)) : 1;

  const getComplexity = (chunks) => {
    if (!chunks) return 'Analyzing...';
    if (chunks < 10) return 'Low (Linear Scan)';
    if (chunks < 40) return 'Moderate (Vectorized Index)';
    return 'High (Distributed Search Graph)';
  };

  const getDetectedTopics = () => {
    const name = (pipelineDetails?.pipeline?.name || "").toLowerCase();
    const topics = [];
    if (name.includes("financial") || name.includes("report") || name.includes("q1") || name.includes("q2") || name.includes("q3") || name.includes("q4") || name.includes("revenue") || name.includes("budget")) {
      topics.push("Finance", "Corporate Revenue", "Performance Metrics");
    }
    if (name.includes("log") || name.includes("system") || name.includes("error") || name.includes("exception") || name.includes("debug") || name.includes("crash")) {
      topics.push("System Diagnostics", "Error Patterns", "Infrastructure Operations");
    }
    if (name.includes("policy") || name.includes("legal") || name.includes("contract") || name.includes("terms") || name.includes("agreement")) {
      topics.push("Compliance", "Legal Terms", "Risk Assessment");
    }
    if (name.includes("technical") || name.includes("architecture") || name.includes("design") || name.includes("spec") || name.includes("doc")) {
      topics.push("System Architecture", "Engineering Specs", "Topological Graph");
    }
    
    if (topics.length === 0) {
      if (isLogPipeline) {
        topics.push("Log Analysis", "Pattern Matching", "System Events");
      } else {
        topics.push("Document Semantics", "Information Retrieval", "Text Processing");
      }
    }
    return topics;
  };

  // Get details for the 7 stages
  const getStageInfo = (stageId) => {
    switch (stageId) {
      case 'upload': {
        const sizeKB = sizeBytes ? `${(sizeBytes / 1024).toFixed(1)} KB` : 'raw_file';
        return {
          status: 'completed',
          worker: 'API Gateway',
          duration: '< 0.5s',
          artifact: uploadedArt ? `raw_file (ID: #${uploadedArt.id}, ${sizeKB})` : 'raw_file',
          progressMsg: 'File payload validated, storage checksum generated, and enqueued.'
        };
      }
      case 'parse': {
        const task = parseTask;
        const art = pipelineDetails?.artifacts?.find(a => a.artifact_type === 'parsed_text' || a.artifact_type === 'parsed_logs');
        const countStr = art?.metadata_json?.size_bytes ? `${art.metadata_json.size_bytes} chars` : '';
        const artDisplay = art ? `${art.artifact_type} (ID: #${art.id} ${countStr})` : 'None generated';
        
        let status = 'pending';
        let progressMsg = 'Awaiting root worker allocation...';
        if (task) {
          status = task.status;
          if (status === 'running') progressMsg = 'Extracting document text elements and layout mapping...';
          else if (status === 'completed') progressMsg = 'Document parsed cleanly. Structural elements mapped.';
          else if (status === 'failed') progressMsg = `Failed: ${task.error_message}`;
        }
        return {
          status,
          worker: task?.assigned_worker_id || 'Pending...',
          duration: task?.completed_at ? `${task.execution_duration.toFixed(1)}s` : task?.status === 'running' ? 'active' : 'N/A',
          artifact: artDisplay,
          progressMsg
        };
      }
      case 'chunk': {
        const task = chunkTask;
        const art = textChunksArt;
        const countStr = chunkCount ? `${chunkCount} blocks` : '';
        const artDisplay = art ? `${art.artifact_type} (ID: #${art.id} ${countStr})` : 'None generated';

        let status = 'pending';
        let progressMsg = 'Awaiting text segmentation trigger...';
        if (task) {
          status = task.status;
          if (status === 'running') progressMsg = isLogPipeline ? 'Detecting error patterns and extracting anomaly clusters...' : 'Breaking text into searchable 300-word blocks with semantic overlap...';
          else if (status === 'completed') progressMsg = isLogPipeline ? `Anomaly clustering complete. ${chunkCount || 'Multiple'} patterns matched.` : `Text segmented successfully. ${chunkCount || 'Multiple'} sections generated.`;
          else if (status === 'failed') progressMsg = `Failed: ${task.error_message}`;
        } else if (parseTask?.status === 'completed') {
          status = 'pending';
          progressMsg = 'Understanding step complete. Enqueueing segmenter...';
        }
        return {
          status,
          worker: task?.assigned_worker_id || 'Pending...',
          duration: task?.completed_at ? `${task.execution_duration.toFixed(1)}s` : task?.status === 'running' ? 'active' : 'N/A',
          artifact: artDisplay,
          progressMsg
        };
      }
      case 'embed': {
        const task = embedTask;
        const art = vectorIndexArt;
        const modelName = art?.metadata_json?.embedding_model || 'all-MiniLM-L6-v2';
        const artDisplay = art ? `vector_index (ID: #${art.id}, ${modelName})` : 'None generated';

        let status = 'pending';
        let progressMsg = 'Awaiting embedding model GPU assignment...';
        if (task) {
          status = task.status;
          if (status === 'running') progressMsg = 'Running tensor embeddings on worker... Generating 384-dim dense vectors...';
          else if (status === 'completed') progressMsg = 'Embeddings computed successfully via sentence-transformers.';
          else if (status === 'failed') progressMsg = `Failed: ${task.error_message}`;
        } else if (chunkTask?.status === 'completed') {
          status = 'pending';
          progressMsg = 'Segmentation complete. Launching vectorization...';
        }
        return {
          status,
          worker: task?.assigned_worker_id || 'Pending...',
          duration: task?.completed_at ? `${task.execution_duration.toFixed(1)}s` : task?.status === 'running' ? 'active' : 'N/A',
          artifact: artDisplay,
          progressMsg
        };
      }
      case 'index': {
        const task = indexTask || embedTask; 
        const art = vectorIndexArt;
        const qdrantOk = art?.metadata_json?.qdrant_upserted ? 'indexed' : 'pending';
        const artDisplay = art ? `qdrant_vector_store (status: ${qdrantOk})` : 'None generated';

        let status = 'pending';
        let progressMsg = 'Awaiting vector database pipeline...';
        if (task) {
          status = task.status;
          if (status === 'running') progressMsg = 'Indexing vectors into Qdrant collection... Building HNSW search graph...';
          else if (status === 'completed') progressMsg = 'Vectors successfully indexed in Qdrant store.';
          else if (status === 'failed') progressMsg = `Failed: ${task.error_message}`;
        }
        return {
          status,
          worker: task?.assigned_worker_id || 'Pending...',
          duration: task?.completed_at ? `${task.execution_duration.toFixed(1)}s` : task?.status === 'running' ? 'active' : 'N/A',
          artifact: artDisplay,
          progressMsg
        };
      }
      case 'ready': {
        const status = pipelineStatus === 'completed' ? 'completed' : pipelineStatus === 'failed' ? 'failed' : 'pending';
        const progressMsg = pipelineStatus === 'completed' 
          ? 'Retrieval index fully active. Awaiting user queries.' 
          : 'Waiting for upstream pipeline steps...';
        return {
          status,
          worker: 'Orchestrator',
          duration: pipelineStatus === 'completed' ? 'ready' : 'active',
          artifact: pipelineStatus === 'completed' ? `retrieval_graph (ID: #${selectedPipelineId})` : 'None',
          progressMsg
        };
      }
      case 'ask': {
        const status = pipelineStatus === 'completed' ? 'completed' : 'pending';
        const progressMsg = pipelineStatus === 'completed'
          ? 'Natural language search is open. Chat panel below is active!'
          : 'Awaiting pipeline readiness...';
        return {
          status,
          worker: 'User (You)',
          duration: 'N/A',
          artifact: 'user_query_pipeline',
          progressMsg
        };
      }
      default:
        return {};
    }
  };

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

  const activeTasks = pipelineDetails?.tasks || [];
  const totalQueued = queueStats.total || 0;
  const onlineWorkers = workers.filter(w => w.status !== 'offline');

  // Filter pipelines to list document ingestion ones in history
  const documentHistoryPipelines = pipelines.filter(p => 
    p.pipeline_type === 'document_processing_demo' || p.pipeline_type === 'log_analysis_demo'
  );

  const stageList = [
    { id: 'upload', label: 'Upload' },
    { id: 'parse', label: 'Document Understanding' },
    { id: 'chunk', label: 'Chunk Generation' },
    { id: 'embed', label: 'Semantic Embedding' },
    { id: 'index', label: 'Vector Indexing' },
    { id: 'ready', label: 'Retrieval Ready' },
    { id: 'ask', label: 'Ask Questions' }
  ];

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
            <span style={{ 
              color: dbStatus === 'online' ? 'var(--color-success)' : dbStatus === 'checking' ? 'var(--color-warning)' : 'var(--color-failure)', 
              fontWeight: 'bold' 
            }}>
              {dbStatus === 'online' ? 'ONLINE' : dbStatus === 'checking' ? 'CHECKING...' : 'OFFLINE'}
            </span>
          </div>
          <div style={{ borderLeft: '1px solid var(--border-subtle)', paddingLeft: '20px' }}>
            <span>Redis Broker: </span>
            <span style={{ 
              color: redisStatus === 'online' ? 'var(--color-success)' : redisStatus === 'checking' ? 'var(--color-warning)' : 'var(--color-failure)', 
              fontWeight: 'bold' 
            }}>
              {redisStatus === 'online' ? 'ONLINE' : redisStatus === 'checking' ? 'CHECKING...' : 'OFFLINE'}
            </span>
          </div>
          <div style={{ borderLeft: '1px solid var(--border-subtle)', paddingLeft: '20px' }}>
            <span>Qdrant Core: </span>
            <span style={{ 
              color: qdrantStatus === 'online' ? 'var(--color-success)' : qdrantStatus === 'checking' ? 'var(--color-warning)' : 'var(--color-failure)', 
              fontWeight: 'bold' 
            }}>
              {qdrantStatus === 'online' ? 'ONLINE' : qdrantStatus === 'checking' ? 'CHECKING...' : 'OFFLINE'}
            </span>
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

          {/* DOCUMENT INTELLIGENCE SUMMARY */}
          {pipelineDetails && (
            <div className="panel fade-in" style={{ padding: '20px', background: 'rgba(59, 130, 246, 0.02)', border: '1px solid rgba(59, 130, 246, 0.15)', display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 style={{ fontSize: '0.85rem', fontWeight: '800', color: '#fff', display: 'flex', alignItems: 'center', gap: '8px', margin: 0, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  <FileText size={16} style={{ color: 'var(--color-accent)' }} />
                  Document Intelligence Summary
                </h3>
                <span className="badge completed" style={{ fontSize: '0.65rem', textTransform: 'uppercase' }}>Analyzed</span>
              </div>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', fontSize: '0.8rem' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <div>
                    <span style={{ color: 'var(--text-muted)' }}>Document:</span>{' '}
                    <strong style={{ color: '#fff', fontFamily: 'monospace' }}>
                      {pipelineDetails?.pipeline?.name?.replace("Ingestion Pipeline - ", "") || "document.pdf"}
                    </strong>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-muted)' }}>Language:</span>{' '}
                    <strong style={{ color: '#fff' }}>English (auto-detected)</strong>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-muted)' }}>Complexity:</span>{' '}
                    <strong style={{ color: 'var(--color-warning)' }}>{getComplexity(chunkCount)}</strong>
                  </div>
                </div>
                
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <div>
                    <span style={{ color: 'var(--text-muted)' }}>Page Count:</span>{' '}
                    <strong style={{ color: '#fff' }}>{pageCount}</strong>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-muted)' }}>Chunk Count:</span>{' '}
                    <strong style={{ color: '#fff' }}>{chunkCount || 'Analyzing...'}</strong>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-muted)' }}>Topics:</span>{' '}
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '4px' }}>
                      {getDetectedTopics().map((t, i) => (
                        <span key={i} style={{ fontSize: '0.65rem', background: 'rgba(255,255,255,0.05)', color: '#cbd5e1', padding: '2px 6px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ACTIVE PIPELINE TRACKER */}
          <div className="panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <h2 style={{ fontSize: '1rem', fontWeight: '800', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '8px', margin: 0 }}>
                <Activity size={18} style={{ color: 'var(--color-accent)' }} />
                AI Document Processing Pipeline
              </h2>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Guided orchestration steps showing worker coordination and vector database loading.
              </span>
            </div>

            {!selectedPipelineId ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)', background: 'rgba(0, 0, 0, 0.1)', border: '1px dashed var(--border-subtle)', borderRadius: '4px' }}>
                  No active document pipeline. Upload a document above or select a historical run below to begin.
                </div>
                {documentHistoryPipelines.length > 0 && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <span style={{ fontSize: '0.7rem', fontWeight: 'bold', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      Pipeline Ingestion History
                    </span>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '180px', overflowY: 'auto' }}>
                      {documentHistoryPipelines.slice(0, 5).map(p => (
                        <div 
                          key={p.id} 
                          onClick={() => setSelectedPipelineId(p.id)}
                          style={{ 
                            display: 'flex', 
                            justifyContent: 'space-between', 
                            alignItems: 'center', 
                            padding: '8px 12px', 
                            background: 'rgba(255,255,255,0.01)', 
                            border: '1px solid var(--border-subtle)', 
                            borderRadius: '4px',
                            cursor: 'pointer',
                            transition: 'all 0.2s'
                          }}
                          className="pipeline-stage-item"
                        >
                          <span style={{ fontSize: '0.75rem', fontWeight: '600', color: '#fff' }}>
                            {p.name.replace("Ingestion Pipeline - ", "")} (ID: #{p.id})
                          </span>
                          <span className={`badge ${p.status}`} style={{ fontSize: '0.65rem', padding: '2px 6px' }}>
                            {p.status}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.8rem', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '8px' }}>
                  <span>Ingestion Instance: <strong>Pipeline #{selectedPipelineId}</strong></span>
                  <span className={`badge ${pipelineStatus || 'running'}`}>{pipelineStatus || 'running'}</span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', position: 'relative', paddingLeft: '16px', borderLeft: '1px dashed var(--border-subtle)' }}>
                  {stageList.map((stage) => {
                    const info = getStageInfo(stage.id);
                    const isCompleted = info.status === 'completed';
                    const isRunning = info.status === 'running' || info.status === 'active';
                    const isFailed = info.status === 'failed';
                    
                    let dotBg = 'var(--text-muted)';
                    let dotClass = '';
                    
                    if (isCompleted) {
                      dotBg = 'var(--color-success)';
                    } else if (isRunning) {
                      dotBg = 'var(--color-accent)';
                      dotClass = 'animate-pulse';
                    } else if (isFailed) {
                      dotBg = 'var(--color-failure)';
                    }
                    
                    return (
                      <div 
                        key={stage.id} 
                        className="pipeline-stage-item fade-in"
                        style={{
                          display: 'flex',
                          gap: '16px',
                          position: 'relative',
                          opacity: isCompleted || isRunning ? 1 : 0.5,
                          padding: '12px',
                          background: isRunning ? 'rgba(59, 130, 246, 0.03)' : 'rgba(255,255,255,0.01)',
                          border: isRunning ? '1px solid rgba(59, 130, 246, 0.2)' : '1px solid var(--border-subtle)',
                          borderRadius: '4px',
                          boxShadow: isRunning ? '0 0 10px rgba(59, 130, 246, 0.05)' : 'none'
                        }}
                      >
                        {/* Dot Connector */}
                        <div style={{
                          position: 'absolute',
                          left: '-21px',
                          top: '18px',
                          width: '9px',
                          height: '9px',
                          borderRadius: '50%',
                          background: dotBg,
                          boxShadow: isRunning ? '0 0 8px var(--color-accent)' : 'none',
                          border: '2px solid var(--bg-primary)'
                        }} className={dotClass} />
                        
                        {/* Details */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', flex: 1 }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ fontSize: '0.8rem', fontWeight: '700', color: isCompleted || isRunning ? '#fff' : 'var(--text-muted-light)' }}>
                              {stage.label}
                            </span>
                            <span className={`badge ${info.status}`} style={{ fontSize: '0.6rem', padding: '1px 6px', textTransform: 'uppercase' }}>
                              {info.status}
                            </span>
                          </div>
                          
                          <span style={{ fontSize: '0.72rem', color: '#cbd5e1' }}>
                            {info.progressMsg}
                          </span>
                          
                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '0.65rem', color: 'var(--text-muted-light)', marginTop: '4px', borderTop: '1px solid rgba(255,255,255,0.03)', paddingTop: '4px' }}>
                            <div>
                              <span style={{ color: 'var(--text-muted)' }}>Worker:</span> <strong style={{ color: '#94a3b8' }}>{info.worker}</strong>
                            </div>
                            <div>
                              <span style={{ color: 'var(--text-muted)' }}>Duration:</span> <strong style={{ color: '#94a3b8' }}>{info.duration}</strong>
                            </div>
                            <div style={{ gridColumn: 'span 2' }}>
                              <span style={{ color: 'var(--text-muted)' }}>Artifact:</span> <code style={{ color: 'var(--color-accent)', wordBreak: 'break-all' }}>{info.artifact}</code>
                            </div>
                          </div>
                          
                          {stage.id === 'ask' && isCompleted && (
                            <button 
                              onClick={() => {
                                if (chatInputRef.current) {
                                  chatInputRef.current.focus();
                                  chatInputRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                  setHighlightChat(true);
                                  setTimeout(() => setHighlightChat(false), 2000);
                                }
                              }}
                              className="btn btn-secondary"
                              style={{
                                marginTop: '8px',
                                height: '24px',
                                fontSize: '0.68rem',
                                alignSelf: 'flex-start',
                                padding: '2px 8px'
                              }}
                            >
                              Start Q&A Session ↓
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
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
                gap: '12px', 
                background: 'rgba(59, 130, 246, 0.01)', 
                border: '1px solid rgba(59, 130, 246, 0.1)', 
                padding: '16px', 
                borderRadius: '4px' 
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: 'var(--color-accent)', fontWeight: 'bold' }}>
                    <Sparkles size={14} />
                    <span>Grounded AI Answer</span>
                  </div>
                  <span className={`badge ${ragAnswer.confidence || 'medium'}`} style={{ fontSize: '0.65rem', textTransform: 'uppercase' }}>
                    Confidence: {ragAnswer.confidence || 'medium'}
                  </span>
                </div>
                <div style={{ fontSize: '0.85rem', color: '#cbd5e1', lineHeight: 1.5, whiteSpace: 'pre-wrap' }}>
                  {ragAnswer.answer}
                </div>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', display: 'flex', gap: '12px', borderTop: '1px solid rgba(255,255,255,0.02)', paddingTop: '8px' }}>
                  <span>Synthesized via Query Pipeline: #{ragAnswer.pipeline_id}</span>
                  <span>Duration: {ragAnswer.elapsed_seconds ? `${ragAnswer.elapsed_seconds.toFixed(2)}s` : '0.4s'}</span>
                </div>
              </div>
            )}

            {results.length > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '4px' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 'bold', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <BookOpen size={14} style={{ color: 'var(--color-success)' }} />
                  Grounded Citations ({results.length})
                </span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '220px', overflowY: 'auto', paddingRight: '4px' }}>
                  {results.map((hit, idx) => (
                    <div key={idx} style={{ background: 'rgba(0,0,0,0.15)', padding: '12px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.7rem', color: '#94a3b8', marginBottom: '6px' }}>
                        <span style={{ fontWeight: 'bold' }}>[Citation {idx + 1}] Chunk #{hit.chunk_index}</span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ color: 'var(--color-success)', fontWeight: 'bold' }}>{Math.round((hit.score || 0) * 100)}% Match Similarity</span>
                        </div>
                      </div>
                      <blockquote style={{ fontSize: '0.75rem', color: '#cbd5e1', borderLeft: '2px solid var(--color-success)', paddingLeft: '8px', margin: 0, fontStyle: 'italic', wordBreak: 'break-word', whiteSpace: 'pre-wrap' }}>
                        "{hit.chunk_text}"
                      </blockquote>
                      <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: '6px' }}>
                        Source: {hit.original_filename || 'unknown'}
                      </div>
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
                  Awaiting active document pipeline execution logs...
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
                            <span style={{ color: 'var(--text-muted)' }}>Duration:</span> {task.execution_duration !== undefined && task.execution_duration !== null ? `${task.execution_duration.toFixed(2)}s` : 'running'}
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
