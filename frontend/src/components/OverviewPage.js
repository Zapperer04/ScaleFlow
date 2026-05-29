import React, { useState, useEffect, useRef } from 'react';
import { 
  Upload, Activity, Database, Search, Sparkles, Loader2, ChevronDown, ChevronUp, FileText, BookOpen, ShieldCheck, ShieldAlert
} from 'lucide-react';
import { 
  createRetrievalPipeline, fetchRetrievalPipelineAnswer, fetchPipelineDetails, fetchPipelineEvents
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
  
  // Live trace events state
  const [traceEvents, setTraceEvents] = useState([]);
  
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

  // Poll active pipeline details and events
  useEffect(() => {
    let detailsTimer;
    let eventsTimer;
    
    if (selectedPipelineId) {
      const getDetails = async () => {
        try {
          const details = await fetchPipelineDetails(selectedPipelineId);
          setPipelineDetails(details);
        } catch (err) {
          console.error('Failed to load active pipeline details:', err);
        }
      };
      
      const getEvents = async () => {
        try {
          const events = await fetchPipelineEvents(selectedPipelineId);
          setTraceEvents(events || []);
        } catch (err) {
          console.error('Failed to load active pipeline events:', err);
        }
      };
      
      getDetails();
      getEvents();
      
      detailsTimer = setInterval(getDetails, 3000);
      eventsTimer = setInterval(getEvents, 2000);
    } else {
      setPipelineDetails(null);
      setTraceEvents([]);
    }
    
    return () => {
      if (detailsTimer) clearInterval(detailsTimer);
      if (eventsTimer) clearInterval(eventsTimer);
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
      
      let document_id = "N/A";
      let filename = "N/A";
      if (pipelineDetails && pipelineDetails.artifacts) {
        const uploadedFile = pipelineDetails.artifacts.find(art => art.artifact_type === 'uploaded_file');
        if (uploadedFile) {
          document_id = uploadedFile.id;
          const meta = typeof uploadedFile.metadata_json === 'string' ? JSON.parse(uploadedFile.metadata_json) : (uploadedFile.metadata_json || {});
          filename = meta.original_filename || "N/A";
        }
      }
      const activeState = pipelineDetails?.pipeline?.status || "N/A";

      console.log("CHAT REQUEST PAYLOAD", pipelinePayload);
      console.log("QUERY:", query);
      console.log("PIPELINE_ID:", selectedPipelineId || "N/A");
      console.log("DOCUMENT_ID:", document_id);
      console.log("FILENAME:", filename);
      console.log("ACTIVE PIPELINE STATE:", activeState);

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
  const qualityGateTask = getTaskByAction('validate_parse_quality');
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

  const getStageExecutionDetails = (taskType) => {
    const task = pipelineDetails?.tasks?.find(t => t.type === taskType);
    const artifactType = {
      'parse_document': 'parsed_text',
      'validate_parse_quality': 'parsed_text',
      'chunk_text': 'text_chunks',
      'generate_embeddings': 'vector_index',
      'summarize_document': 'summary',
      'parse_logs': 'parsed_logs',
      'detect_error_patterns': 'error_patterns',
      'summarize_logs': 'log_summary'
    }[taskType];
    
    const art = task 
      ? pipelineDetails?.artifacts?.find(a => a.task_id === task.id)
      : pipelineDetails?.artifacts?.find(a => a.artifact_type === artifactType);
    let artifactDisplay = 'None';
    if (art) {
      const sizeKB = art.metadata_json?.size_bytes ? ` (${(art.metadata_json.size_bytes / 1024).toFixed(1)} KB)` : '';
      const countBlocks = art.metadata_json?.vector_count ? ` (${art.metadata_json.vector_count} blocks)` : '';
      artifactDisplay = `${art.artifact_type} (ID: #${art.id}${sizeKB}${countBlocks})`;
    }
    
    if (!task) {
      return {
        status: 'PENDING',
        workerId: 'N/A',
        startTime: 'N/A',
        completionTime: 'N/A',
        duration: 'N/A',
        retries: 0,
        errors: 'N/A',
        artifact: 'N/A'
      };
    }
    
    // Map status
    let mappedStatus = task.status.toUpperCase();
    if (task.status === 'pending') {
      mappedStatus = task.retry_count > 0 ? 'RETRYING' : 'QUEUED';
    } else if (task.status === 'running') {
      mappedStatus = task.started_at ? 'EXECUTING' : 'DEQUEUED';
    }
    
    const formatTime = (timeStr) => {
      if (!timeStr) return 'N/A';
      return new Date(timeStr).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    };
    
    return {
      status: mappedStatus,
      workerId: task.assigned_worker_id || 'N/A',
      startTime: formatTime(task.started_at),
      completionTime: formatTime(task.completed_at),
      duration: task.execution_duration !== null && task.execution_duration !== undefined ? `${task.execution_duration.toFixed(2)}s` : task.status === 'running' ? 'Active' : 'N/A',
      retries: task.retry_count || 0,
      errors: task.error_message || 'None',
      artifact: artifactDisplay
    };
  };

  const stagesToRender = isLogPipeline ? [
    { type: 'parse_logs', label: 'Parse Logs' },
    { type: 'detect_error_patterns', label: 'Detect Error Patterns' },
    { type: 'generate_embeddings', label: 'Generate Embeddings' },
    { type: 'summarize_logs', label: 'Summarize Logs' }
  ] : [
    { type: 'parse_document', label: 'Parse Document' },
    { type: 'validate_parse_quality', label: 'Parse Quality Gate' },
    { type: 'chunk_text', label: 'Chunk Text' },
    { type: 'generate_embeddings', label: 'Generate Embeddings' },
    { type: 'summarize_document', label: 'Summarize Document' }
  ];

  const activeTasks = pipelineDetails?.tasks || [];
  const totalQueued = queueStats.total || 0;
  const onlineWorkers = workers.filter(w => w.status !== 'offline');

  // Filter pipelines to list document ingestion ones in history
  const documentHistoryPipelines = pipelines.filter(p => 
    p.pipeline_type === 'document_processing_demo' || p.pipeline_type === 'log_analysis_demo'
  );

  const renderConsoleHeader = () => {
    if (!pipelineDetails) return null;
    const pipeline = pipelineDetails.pipeline;
    const currentTask = pipelineDetails.tasks?.find(t => t.status !== 'completed' && t.status !== 'failed');
    const failedTask = pipelineDetails.tasks?.find(t => t.status === 'failed');
    const currentStageLabel = failedTask
      ? `FAILED: ${failedTask.type.replace(/_/g, ' ').toUpperCase()}`
      : currentTask 
        ? currentTask.type.replace(/_/g, ' ').toUpperCase()
        : 'COMPLETED';
      
    const getElapsedRuntime = () => {
      if (!pipeline) return '0s';
      const start = new Date(pipeline.started_at || pipeline.created_at);
      const end = pipeline.completed_at ? new Date(pipeline.completed_at) : new Date();
      const diffSec = Math.max(0, Math.round((end - start) / 1000));
      return `${diffSec}s`;
    };
    
    const activeWorker = pipelineDetails.tasks?.find(t => t.status === 'running')?.assigned_worker_id
      || failedTask?.assigned_worker_id
      || 'None';

    const isFailed = pipeline.status === 'failed' || !!failedTask;
    
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <div className="panel" style={{ padding: '16px 20px', display: 'flex', flexWrap: 'wrap', gap: '20px', justifyContent: 'space-between', alignItems: 'center', background: isFailed ? 'rgba(239, 68, 68, 0.04)' : 'rgba(30, 41, 59, 0.4)', border: isFailed ? '1px solid rgba(239, 68, 68, 0.2)' : '1px solid rgba(255,255,255,0.05)', borderRadius: '6px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 'bold', textTransform: 'uppercase' }}>Pipeline ID</span>
            <strong style={{ color: '#fff', fontSize: '1rem', fontFamily: 'monospace' }}>#{selectedPipelineId}</strong>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 'bold', textTransform: 'uppercase' }}>Current Stage</span>
            <strong style={{ color: isFailed ? 'var(--color-failure)' : 'var(--color-accent)', fontSize: '0.9rem' }}>{currentStageLabel}</strong>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 'bold', textTransform: 'uppercase' }}>Status</span>
            <span className={`badge ${pipeline.status}`} style={{ fontSize: '0.7rem', padding: '2px 8px', textTransform: 'uppercase' }}>
              {pipeline.status}
            </span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 'bold', textTransform: 'uppercase' }}>Elapsed Runtime</span>
            <strong style={{ color: '#fff', fontSize: '0.9rem' }}>{getElapsedRuntime()}</strong>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 'bold', textTransform: 'uppercase' }}>Active Worker</span>
            <strong style={{ color: '#cbd5e1', fontSize: '0.9rem', fontFamily: 'monospace' }}>{activeWorker}</strong>
          </div>
        </div>
        {isFailed && failedTask?.error_message && (
          <div style={{
            padding: '10px 16px',
            background: 'rgba(239, 68, 68, 0.06)',
            border: '1px solid rgba(239, 68, 68, 0.2)',
            borderRadius: '4px',
            fontSize: '0.75rem',
            color: '#fca5a5',
            display: 'flex',
            gap: '8px',
            alignItems: 'flex-start'
          }}>
            <span style={{ color: 'var(--color-failure)', fontWeight: 'bold', flexShrink: 0 }}>FAILURE REASON:</span>
            <span style={{ wordBreak: 'break-word' }}>{failedTask.error_message}</span>
          </div>
        )}
      </div>
    );
  };

  const renderStagesTable = () => {
    return (
      <div className="panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px', borderRadius: '6px' }}>
        <h3 style={{ fontSize: '0.85rem', fontWeight: '800', color: '#fff', textTransform: 'uppercase', letterSpacing: '0.5px', margin: 0 }}>
          Pipeline Execution Stages
        </h3>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.75rem', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)' }}>
                <th style={{ padding: '8px 4px' }}>Stage</th>
                <th style={{ padding: '8px 4px' }}>Status</th>
                <th style={{ padding: '8px 4px' }}>Worker</th>
                <th style={{ padding: '8px 4px' }}>Start Time</th>
                <th style={{ padding: '8px 4px' }}>End Time</th>
                <th style={{ padding: '8px 4px' }}>Duration</th>
                <th style={{ padding: '8px 4px' }}>Retries</th>
                <th style={{ padding: '8px 4px' }}>Errors</th>
                <th style={{ padding: '8px 4px' }}>Generated Artifact</th>
              </tr>
            </thead>
            <tbody>
              {stagesToRender.map((stage) => {
                const info = getStageExecutionDetails(stage.type);
                let statusColor = 'var(--text-muted)';
                if (info.status === 'COMPLETED') statusColor = 'var(--color-success)';
                else if (info.status === 'EXECUTING') statusColor = 'var(--color-accent)';
                else if (info.status === 'FAILED') statusColor = 'var(--color-failure)';
                else if (info.status === 'RETRYING') statusColor = 'var(--color-warning)';
                else if (info.status === 'DEQUEUED') statusColor = '#a855f7'; // Purple
                else if (info.status === 'QUEUED') statusColor = '#3b82f6'; // Blue
                
                return (
                  <tr key={stage.type} style={{ borderBottom: '1px solid rgba(255,255,255,0.02)', color: '#cbd5e1' }}>
                    <td style={{ padding: '8px 4px', fontWeight: 'bold' }}>{stage.label}</td>
                    <td style={{ padding: '8px 4px' }}>
                      <span style={{
                        color: statusColor,
                        fontWeight: 'bold',
                        fontSize: '0.7rem',
                        background: 'rgba(255,255,255,0.02)',
                        padding: '2px 6px',
                        borderRadius: '3px',
                        border: `1px solid ${statusColor}44`
                      }}>{info.status}</span>
                    </td>
                    <td style={{ padding: '8px 4px', fontFamily: 'monospace' }}>{info.workerId}</td>
                    <td style={{ padding: '8px 4px' }}>{info.startTime}</td>
                    <td style={{ padding: '8px 4px' }}>{info.completionTime}</td>
                    <td style={{ padding: '8px 4px' }}>{info.duration}</td>
                    <td style={{ padding: '8px 4px', textAlign: 'center' }}>{info.retries}</td>
                    <td style={{ 
                      padding: '8px 4px', 
                      color: info.errors !== 'None' ? 'var(--color-failure)' : '#cbd5e1',
                      maxWidth: '120px',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap'
                    }} title={info.errors}>{info.errors}</td>
                    <td style={{ padding: '8px 4px' }}><code style={{ fontSize: '0.68rem', color: 'var(--color-accent)' }}>{info.artifact}</code></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  const renderQualityGatePanel = () => {
    if (!qualityGateTask) return null;

    const art = pipelineDetails?.artifacts?.find(a => a.task_id === qualityGateTask.id);
    const metadata = art?.metadata_json || {};
    
    // Status
    const isCompleted = qualityGateTask.status === 'completed';
    const isFailed = qualityGateTask.status === 'failed';

    return (
      <div className="panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px', borderRadius: '6px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ fontSize: '0.85rem', fontWeight: '800', color: '#fff', textTransform: 'uppercase', letterSpacing: '0.5px', margin: 0, display: 'flex', alignItems: 'center', gap: '6px' }}>
            {isFailed ? (
              <ShieldAlert size={16} style={{ color: 'var(--color-failure)' }} />
            ) : (
              <ShieldCheck size={16} style={{ color: isCompleted ? 'var(--color-success)' : 'var(--text-muted)' }} />
            )}
            Ingestion Parse Quality Gate
          </h3>
          <span className={`badge ${qualityGateTask.status}`} style={{ fontSize: '0.65rem', textTransform: 'uppercase' }}>
            {qualityGateTask.status}
          </span>
        </div>

        {/* Metrics Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '10px' }}>
          <div style={{ background: 'rgba(0,0,0,0.15)', padding: '10px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 'bold' }}>PARSER USED</div>
            <div style={{ fontSize: '0.9rem', color: '#fff', fontWeight: 'bold', fontFamily: 'monospace', marginTop: '4px' }}>
              {isCompleted ? String(metadata.parser_used || 'N/A').toUpperCase() : 'PENDING'}
            </div>
          </div>
          <div style={{ background: 'rgba(0,0,0,0.15)', padding: '10px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 'bold' }}>OCR ACTIVATED</div>
            <div style={{ fontSize: '0.9rem', color: metadata.ocr_activated ? 'var(--color-warning)' : '#fff', fontWeight: 'bold', marginTop: '4px' }}>
              {isCompleted ? (metadata.ocr_activated ? 'YES' : 'NO') : 'PENDING'}
            </div>
          </div>
          <div style={{ background: 'rgba(0,0,0,0.15)', padding: '10px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 'bold' }}>OCR CONFIDENCE</div>
            <div style={{ fontSize: '0.9rem', color: '#fff', fontWeight: 'bold', marginTop: '4px' }}>
              {isCompleted ? (metadata.ocr_activated ? `${(metadata.ocr_confidence || 0).toFixed(1)}%` : 'N/A') : 'PENDING'}
            </div>
          </div>
          <div style={{ background: 'rgba(0,0,0,0.15)', padding: '10px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 'bold' }}>PRINTABLE CHAR RATIO</div>
            <div style={{ fontSize: '0.9rem', color: isCompleted && metadata.printable_ratio < 0.85 ? 'var(--color-failure)' : '#fff', fontWeight: 'bold', marginTop: '4px' }}>
              {isCompleted ? `${((metadata.printable_ratio || 0) * 100).toFixed(1)}%` : 'PENDING'}
            </div>
          </div>
          <div style={{ background: 'rgba(0,0,0,0.15)', padding: '10px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 'bold' }}>DICTIONARY-WORD RATIO</div>
            <div style={{ fontSize: '0.9rem', color: isCompleted && metadata.dict_word_ratio < 0.40 ? 'var(--color-failure)' : '#fff', fontWeight: 'bold', marginTop: '4px' }}>
              {isCompleted ? `${((metadata.dict_word_ratio || 0) * 100).toFixed(1)}%` : 'PENDING'}
            </div>
          </div>
          <div style={{ background: 'rgba(0,0,0,0.15)', padding: '10px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 'bold' }}>TEXT COHERENCE SCORE</div>
            <div style={{ fontSize: '0.9rem', color: isCompleted && metadata.coherence_score < 60.0 ? 'var(--color-failure)' : '#fff', fontWeight: 'bold', marginTop: '4px' }}>
              {isCompleted ? `${(metadata.coherence_score || 0).toFixed(1)}/100` : 'PENDING'}
            </div>
          </div>
        </div>

        {/* Text Preview */}
        {isCompleted && metadata.preview && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div style={{ fontSize: '0.7rem', fontWeight: 'bold', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Parsed Text Preview (First 1,000 Characters)</div>
            <pre style={{
              background: 'rgba(0,0,0,0.25)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '4px',
              padding: '12px',
              margin: 0,
              fontSize: '0.7rem',
              color: '#cbd5e1',
              fontFamily: 'monospace',
              whiteSpace: 'pre-wrap',
              maxHeight: '180px',
              overflowY: 'auto',
              lineHeight: '1.4'
            }}>
              {metadata.preview}
            </pre>
          </div>
        )}

        {isFailed && (
          <div style={{
            padding: '10px 16px',
            background: 'rgba(239, 68, 68, 0.06)',
            border: '1px solid rgba(239, 68, 68, 0.2)',
            borderRadius: '4px',
            fontSize: '0.75rem',
            color: '#fca5a5',
            lineHeight: 1.4
          }}>
            <strong style={{ color: 'var(--color-failure)' }}>GATE BLOCKED: </strong>
            <span>{qualityGateTask.error_message || 'Document quality is below readable thresholds.'}</span>
          </div>
        )}
      </div>
    );
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

      {/* 2. SPLIT LAYOUT */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(280px, 1.8fr) minmax(220px, 1.2fr)', gap: '20px' }}>
        
        {/* LEFT COLUMN: UPLOAD, CONSOLE HEADER, STAGES TABLE, & RAG CHAT */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {/* UPLOAD PANEL */}
          <div className="panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px', borderRadius: '6px' }}>
            <div>
              <h2 style={{ fontSize: '1rem', fontWeight: '800', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '8px', margin: 0 }}>
                <Upload size={18} style={{ color: 'var(--color-accent)' }} />
                AI Document Ingestion
              </h2>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Upload unstructured text documents to trigger the distributed pipeline.
              </span>
            </div>

            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <select 
                  value={fileType}
                  onChange={(e) => setFileType(e.target.value)}
                  style={{ width: '100%', maxWidth: '420px', boxSizing: 'border-box' }}
                >
                  <option value="document_processing_demo">Standard AI Document Ingestion (.txt)</option>
                  <option value="document_processing_demo">PDF Document Ingestion (.pdf)</option>
                </select>
              </div>

              <label className="btn btn-primary" style={{ height: '28px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', cursor: uploading ? 'not-allowed' : 'pointer', boxSizing: 'border-box' }}>
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

          {/* ACTIVE PIPELINE RUNTIME CONSOLE */}
          {selectedPipelineId && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }} className="fade-in">
              {renderConsoleHeader()}
              {renderStagesTable()}
              {renderQualityGatePanel()}
            </div>
          )}

          {/* CHAT WITH DOCUMENT PANEL (RAG) */}
          <div 
            className="panel" 
            style={{ 
              padding: '24px', 
              display: 'flex', 
              flexDirection: 'column', 
              gap: '16px',
              border: highlightChat ? '1px solid var(--color-accent)' : '1px solid var(--border-subtle)',
              borderRadius: '6px',
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
                placeholder={selectedPipelineId ? "Ask a question about this document..." : "Select an ingestion pipeline from history or upload a file first..."}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                disabled={ragLoading}
                style={{ flex: 1, height: '28px', maxWidth: '100%', boxSizing: 'border-box', padding: '6px 8px' }}
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
                borderRadius: '6px' 
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

        {/* RIGHT COLUMN: LIVE TRACE STREAM & HISTORICAL SELECTOR */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {selectedPipelineId ? (
            <LiveTraceStream events={traceEvents} />
          ) : (
            <div className="panel" style={{ padding: '20px', background: 'rgba(0,0,0,0.2)', border: '1px dashed var(--border-subtle)', borderRadius: '6px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8rem', padding: '60px 20px' }}>
              Select a pipeline from the history below or upload a new file to watch live execution traces.
            </div>
          )}

          {/* HISTORICAL PIPELINES SELECTOR */}
          <div className="panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '12px', borderRadius: '6px' }}>
            <span style={{ fontSize: '0.7rem', fontWeight: 'bold', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Pipeline Ingestion History
            </span>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '200px', overflowY: 'auto' }}>
              {documentHistoryPipelines.length === 0 ? (
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontStyle: 'italic', padding: '8px' }}>
                  No historical pipelines found.
                </span>
              ) : (
                documentHistoryPipelines.map(p => (
                  <div 
                    key={p.id} 
                    onClick={() => setSelectedPipelineId(p.id)}
                    style={{ 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'center', 
                      padding: '8px 12px', 
                      background: selectedPipelineId === p.id ? 'rgba(59, 130, 246, 0.08)' : 'rgba(255,255,255,0.01)', 
                      border: selectedPipelineId === p.id ? '1px solid rgba(59, 130, 246, 0.3)' : '1px solid var(--border-subtle)', 
                      borderRadius: '4px',
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                      wordBreak: 'break-word'
                    }}
                    className="pipeline-stage-item"
                  >
                    <span style={{ fontSize: '0.75rem', fontWeight: '600', color: selectedPipelineId === p.id ? '#5B8CFF' : '#fff', maxWidth: '75%', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {(p.name || String(p.id)).replace?.("Ingestion Pipeline - ", "") || `Pipeline ${p.id}`} (ID: #{p.id})
                    </span>
                    <span className={`badge ${p.status}`} style={{ fontSize: '0.65rem', padding: '2px 6px', textTransform: 'uppercase' }}>
                      {p.status}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>

        </div>

      </div>

    </div>
  );
};

const LiveTraceStream = ({ events }) => {
  const terminalRef = useRef(null);
  const [filter, setFilter] = useState('ALL'); // ALL, INFO, WARN, ERROR
  const [autoScroll, setAutoScroll] = useState(true);

  // Handle scroll events to toggle auto-scroll
  const handleScroll = () => {
    if (!terminalRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = terminalRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
    setAutoScroll(isAtBottom);
  };

  useEffect(() => {
    if (autoScroll && terminalRef.current) {
      terminalRef.current.scrollTo({
        top: terminalRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [events, autoScroll]);

  const filteredEvents = events.filter(e => {
    if (filter === 'ALL') return true;
    const type = e.event_type.toLowerCase();
    const cat = e.event_category?.toLowerCase() || '';
    const msg = e.message?.toLowerCase() || '';
    
    if (filter === 'ERROR') {
      return cat === 'critical' || type.includes('fail') || msg.includes('fail') || msg.includes('error');
    }
    if (filter === 'WARN') {
      return type.includes('retry') || type.includes('recover') || msg.includes('retry');
    }
    if (filter === 'INFO') {
      return !(cat === 'critical' || type.includes('fail') || msg.includes('fail') || msg.includes('error') || type.includes('retry') || type.includes('recover'));
    }
    return true;
  });

  return (
    <div style={{
      background: '#0a0f1d',
      border: '1px solid var(--border-subtle)',
      borderRadius: '6px',
      padding: '0',
      fontFamily: 'monospace',
      fontSize: '0.75rem',
      height: '420px',
      display: 'flex',
      flexDirection: 'column',
      boxShadow: 'inset 0 0 10px rgba(0,0,0,0.5)',
      overflow: 'hidden',
      position: 'relative'
    }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        background: 'rgba(255,255,255,0.02)',
        borderBottom: '1px solid rgba(255,255,255,0.05)',
        padding: '10px 16px',
        color: '#94a3b8',
        fontSize: '0.7rem',
        textTransform: 'uppercase',
        letterSpacing: '1px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10b981', display: 'inline-block' }} className="animate-pulse" />
          <span style={{ fontWeight: 'bold', color: '#fff' }}>Execution Trace</span>
        </div>
        
        <div style={{ display: 'flex', gap: '6px' }}>
          {['ALL', 'INFO', 'WARN', 'ERROR'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              style={{
                background: filter === f ? 'rgba(59, 130, 246, 0.2)' : 'transparent',
                color: filter === f ? '#60a5fa' : '#64748b',
                border: `1px solid ${filter === f ? '#3b82f6' : 'transparent'}`,
                borderRadius: '4px',
                padding: '2px 8px',
                fontSize: '0.65rem',
                cursor: 'pointer',
                transition: 'all 0.2s'
              }}
            >
              {f}
            </button>
          ))}
        </div>
      </div>
      
      <div 
        style={{
          flex: 1,
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: '2px',
          padding: '12px 16px'
        }} 
        ref={terminalRef}
        onScroll={handleScroll}
      >
        {filteredEvents.length === 0 ? (
          <div style={{ color: '#475569', fontStyle: 'italic', textAlign: 'center', marginTop: '120px' }}>
            No matching trace logs found...
          </div>
        ) : (
          filteredEvents.map((e, idx) => {
            let color = '#e2e8f0'; // default white
            const type = e.event_type.toLowerCase();
            const cat = e.event_category?.toLowerCase() || '';
            const msg = e.message || '';
            
            if (cat === 'critical' || type.includes('fail') || msg.includes('fail') || msg.includes('error')) {
              color = '#f87171'; // soft red
            } else if (type.includes('retry') || type.includes('recover') || msg.includes('retry')) {
              color = '#fbbf24'; // orange/yellow
            } else if (type.includes('complete') || type.includes('success') || msg.includes('success') || msg.includes('completed')) {
              color = '#34d399'; // green
            } else if (type === 'task_trace' || type.includes('progress')) {
              color = '#60a5fa'; // blue
            } else if (type.includes('claim') || type.includes('start')) {
              color = '#c084fc'; // purple
            } else if (type.includes('create') || type.includes('queue')) {
              color = '#94a3b8'; // slate
            }

            const timeStr = e.created_at ? new Date(e.created_at).toLocaleTimeString([], {hour12: false, hour: '2-digit', minute:'2-digit', second:'2-digit'}) : 'N/A';
            const workerTag = e.worker_id ? `[${e.worker_id.split('-').pop()}]` : '[SYSTEM]';

            return (
              <div key={e.id || idx} style={{ color, display: 'flex', gap: '10px', lineHeight: '1.5' }}>
                <span style={{ color: '#475569', flexShrink: 0, width: '65px' }}>{timeStr}</span>
                <span style={{ color: '#64748b', flexShrink: 0, width: '60px', fontWeight: 'bold' }}>{workerTag}</span>
                <span style={{ flex: 1, wordBreak: 'break-word', opacity: 0.9 }}>
                  {msg}
                </span>
              </div>
            );
          })
        )}
      </div>
      
      {!autoScroll && (
        <div 
          onClick={() => {
            setAutoScroll(true);
            if (terminalRef.current) {
              terminalRef.current.scrollTo({ top: terminalRef.current.scrollHeight, behavior: 'smooth' });
            }
          }}
          style={{
            position: 'absolute',
            bottom: '20px',
            right: '40px',
            background: 'var(--color-accent)',
            color: '#fff',
            padding: '4px 12px',
            borderRadius: '12px',
            fontSize: '0.65rem',
            cursor: 'pointer',
            boxShadow: '0 2px 5px rgba(0,0,0,0.5)',
            fontWeight: 'bold'
          }}
        >
          ↓ Auto-scroll paused
        </div>
      )}
    </div>
  );
};

export default OverviewPage;
