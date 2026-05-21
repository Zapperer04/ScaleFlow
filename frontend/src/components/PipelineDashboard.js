import React, { useState, useEffect } from 'react';
import { 
  GitBranch, Play, X, RefreshCw, FileText, CheckCircle2, 
  XCircle, AlertTriangle, Clock, ChevronRight, Activity, Trash2, Upload
} from 'lucide-react';
import { 
  fetchPipelines, fetchPipelineDetails, createPipeline, 
  cancelPipeline, runPipelineTests, fetchArtifactContent,
  uploadFile, fetchUploadedFiles, fetchUploadedFileDetail
} from '../services/api';

const DEFAULT_PAYLOADS = {
  document_processing_demo: {
    source_text: "ScaleFlow DAG Orchestration makes distributed workflows extremely reliable and artifact-driven."
  },
  log_analysis_demo: {
    source_text: "2026-05-21 12:00:01 ERROR: Database connection failed after 3 retries\n2026-05-21 12:00:05 WARNING: Redis connection timeout, retrying...\n2026-05-21 12:00:10 INFO: System health check passed"
  }
};

const PipelineDashboard = () => {
  const [pipelines, setPipelines] = useState([]);
  const [selectedPipelineId, setSelectedPipelineId] = useState(null);
  const [selectedPipelineData, setSelectedPipelineData] = useState(null);
  const [pipelineType, setPipelineType] = useState('document_processing_demo');
  const [pipelineName, setPipelineName] = useState('Demo Document Pipeline');
  const [payloadText, setPayloadText] = useState(JSON.stringify(DEFAULT_PAYLOADS.document_processing_demo, null, 2));
  
  // Test running state
  const [testing, setTesting] = useState(false);
  const [testResults, setTestResults] = useState(null);
  const [showTestModal, setShowTestModal] = useState(false);

  // Selected Artifact State
  const [activeArtifact, setActiveArtifact] = useState(null);
  const [artifactLoading, setArtifactLoading] = useState(false);

  // File Ingestion State
  const [selectedFile, setSelectedFile] = useState(null);
  const [ingestPipelineType, setIngestPipelineType] = useState('auto');
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState(null);
  const [uploadedFiles, setUploadedFiles] = useState([]);

  // Sync pipelines list
  const loadPipelinesList = async () => {
    try {
      const data = await fetchPipelines();
      setPipelines(data);
    } catch (err) {
      console.error('Failed to load pipelines:', err);
    }
  };

  // Sync uploaded files list
  const loadUploadedFilesList = async () => {
    try {
      const data = await fetchUploadedFiles();
      setUploadedFiles(data);
    } catch (err) {
      console.error('Failed to load uploaded files:', err);
    }
  };

  // Sync selected pipeline details
  const loadPipelineDetails = async (id) => {
    try {
      const data = await fetchPipelineDetails(id);
      setSelectedPipelineData(data);
    } catch (err) {
      console.error('Failed to load pipeline details:', err);
    }
  };

  useEffect(() => {
    loadPipelinesList();
    loadUploadedFilesList();
    const interval = setInterval(() => {
      loadPipelinesList();
      loadUploadedFilesList();
      if (selectedPipelineId) {
        loadPipelineDetails(selectedPipelineId);
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [selectedPipelineId]);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFile(e.target.files[0]);
      setUploadMessage(null);
    }
  };

  const handleFileUpload = async (e) => {
    e.preventDefault();
    if (!selectedFile) {
      alert('Please select a file first.');
      return;
    }
    setUploading(true);
    setUploadMessage('Uploading...');
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('pipeline_type', ingestPipelineType);

      const res = await uploadFile(formData);
      setUploadMessage('File uploaded successfully! Starting ingestion...');
      setSelectedFile(null);
      
      const fileInput = document.getElementById('ingest-file-picker');
      if (fileInput) fileInput.value = '';
      
      setSelectedPipelineId(res.pipeline_id);
      loadUploadedFilesList();
      loadPipelinesList();
    } catch (err) {
      console.error('Upload failed:', err);
      setUploadMessage('Upload failed: ' + (err.response?.data?.error || err.message));
    } finally {
      setUploading(false);
    }
  };

  // Update default payload & name when template type changes
  const handleTypeChange = (type) => {
    setPipelineType(type);
    setPayloadText(JSON.stringify(DEFAULT_PAYLOADS[type], null, 2));
    if (type === 'document_processing_demo') {
      setPipelineName('Demo Document Pipeline');
    } else {
      setPipelineName('Demo Log Analysis Pipeline');
    }
  };

  // Handle pipeline creation
  const handleCreatePipeline = async (e) => {
    e.preventDefault();
    try {
      let initialPayload = {};
      try {
        initialPayload = JSON.parse(payloadText);
      } catch (err) {
        alert('Invalid JSON in payload. Please correct it before submitting.');
        return;
      }

      const res = await createPipeline({
        name: pipelineName,
        pipeline_type: pipelineType,
        initial_payload: initialPayload
      });

      setSelectedPipelineId(res.pipeline_id);
      loadPipelinesList();
    } catch (err) {
      console.error('Failed to create pipeline:', err);
      alert('Error creating pipeline: ' + (err.response?.data?.error || err.message));
    }
  };

  // Handle pipeline cancel
  const handleCancelPipeline = async (id) => {
    try {
      await cancelPipeline(id);
      loadPipelinesList();
      if (selectedPipelineId === id) {
        loadPipelineDetails(id);
      }
    } catch (err) {
      console.error('Failed to cancel pipeline:', err);
      alert('Error cancelling pipeline: ' + (err.response?.data?.error || err.message));
    }
  };

  // Handle integration test execution
  const handleRunPipelineTests = async () => {
    setTesting(true);
    setTestResults(null);
    setShowTestModal(true);
    try {
      const data = await runPipelineTests();
      setTestResults(data);
      loadPipelinesList();
    } catch (err) {
      setTestResults({
        status: 'failed',
        logs: ['Integration test run failed.'],
        error: err.response?.data?.error || err.message
      });
    } finally {
      setTesting(false);
    }
  };

  // Handle viewing artifact content
  const handleViewArtifact = async (artifact) => {
    setArtifactLoading(true);
    setActiveArtifact(null);
    try {
      const data = await fetchArtifactContent(artifact.id);
      setActiveArtifact(data);
    } catch (err) {
      console.error('Failed to fetch artifact content:', err);
      setActiveArtifact({
        id: artifact.id,
        artifact_type: artifact.artifact_type,
        content: { error: "Failed to load artifact content from disk: " + (err.response?.data?.error || err.message) }
      });
    } finally {
      setArtifactLoading(false);
    }
  };

  // Compute DAG stage level for visualization layout
  const getDagStages = () => {
    if (!selectedPipelineData || !selectedPipelineData.tasks) return [];
    const tasks = selectedPipelineData.tasks;
    
    // Map tasks by id
    const taskMap = {};
    tasks.forEach(t => {
      taskMap[t.id] = { ...t, children: [], parents: [] };
    });

    // Populate relations
    tasks.forEach(t => {
      const deps = t.dependencies || [];
      deps.forEach(parentId => {
        if (taskMap[parentId]) {
          taskMap[t.id].parents.push(parentId);
          taskMap[parentId].children.push(t.id);
        }
      });
    });

    // Compute stage ranks using topological progression
    const rankMap = {};
    let changed = true;
    
    // Initialize roots
    tasks.forEach(t => {
      if ((t.dependencies || []).length === 0) {
        rankMap[t.id] = 0;
      }
    });

    while (changed) {
      changed = false;
      tasks.forEach(t => {
        if (rankMap[t.id] === undefined) {
          const parentRanks = t.dependencies
            .map(pId => rankMap[pId])
            .filter(r => r !== undefined);
            
          // If all parents have computed ranks
          if (parentRanks.length === t.dependencies.length) {
            const maxParentRank = Math.max(...parentRanks);
            rankMap[t.id] = maxParentRank + 1;
            changed = true;
          }
        }
      });
    }

    // Group tasks by their calculated stage
    const stages = [];
    tasks.forEach(t => {
      const rank = rankMap[t.id] !== undefined ? rankMap[t.id] : 0;
      if (!stages[rank]) stages[rank] = [];
      stages[rank].push(taskMap[t.id]);
    });

    return stages.filter(Boolean);
  };

  const stages = getDagStages();

  const getStatusBadgeClass = (status) => {
    switch (status) {
      case 'completed': return 'badge-completed';
      case 'running': return 'badge-running';
      case 'failed': return 'badge-failed';
      case 'blocked': return 'badge-blocked';
      case 'cancelled': return 'badge-cancelled';
      default: return 'badge-pending';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed': return <CheckCircle2 size={14} className="text-green" />;
      case 'running': return <Activity size={14} className="text-blue animate-pulse-slow" />;
      case 'failed': return <XCircle size={14} className="text-red" />;
      case 'blocked': return <AlertTriangle size={14} className="text-amber" />;
      case 'cancelled': return <XCircle size={14} className="text-gray" />;
      default: return <Clock size={14} className="text-slate" />;
    }
  };

  return (
    <div className="panel execution-log" style={{ gridColumn: 'span 12', marginTop: '24px' }}>
      <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h2 style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <GitBranch size={22} className="text-purple" style={{ color: '#8b5cf6' }} />
            Pipeline DAG Orchestration
          </h2>
          <span className="panel-subtitle">Manage dependent task pipelines & artifact-based communications</span>
        </div>
        
        <button 
          onClick={handleRunPipelineTests}
          disabled={testing}
          style={{
            background: 'linear-gradient(135deg, #a78bfa 0%, #8b5cf6 100%)',
            color: '#ffffff',
            border: 'none',
            borderRadius: '8px',
            padding: '8px 18px',
            fontSize: '0.85rem',
            fontWeight: '600',
            cursor: testing ? 'not-allowed' : 'pointer',
            boxShadow: '0 4px 14px rgba(139, 92, 246, 0.25)',
            transition: 'all 0.2s ease',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          {testing ? <RefreshCw className="animate-spin" size={14} /> : <Play size={14} />}
          {testing ? 'Running DAG Tests...' : 'Run Pipeline Tests'}
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(12, 1fr)', gap: '24px', marginTop: '20px' }}>
        {/* Left Side: Create Form + Active Pipelines List */}
        <div style={{ gridColumn: 'span 4', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {/* File Ingestion Card */}
          <div style={{ background: 'rgba(15, 23, 42, 0.3)', border: '1px solid rgba(148, 163, 184, 0.1)', borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: '700', marginBottom: '16px', color: '#f1f5f9', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Upload size={18} className="text-pink" style={{ color: '#ec4899' }} />
              File Ingestion (Phase 3)
            </h3>
            <form onSubmit={handleFileUpload} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div className="form-field" style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Select Unstructured File</label>
                <input 
                  id="ingest-file-picker"
                  type="file" 
                  onChange={handleFileChange} 
                  required 
                  style={{ 
                    fontSize: '0.85rem', 
                    padding: '8px', 
                    background: 'rgba(15, 23, 42, 0.5)', 
                    border: '1px dashed rgba(148, 163, 184, 0.2)',
                    borderRadius: '6px',
                    color: '#e2e8f0',
                    cursor: 'pointer'
                  }}
                />
              </div>

              <div className="form-field" style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Pipeline Template</label>
                <select 
                  value={ingestPipelineType} 
                  onChange={(e) => setIngestPipelineType(e.target.value)}
                  style={{ fontSize: '0.9rem', padding: '10px' }}
                >
                  <option value="auto">Auto-Detect from Extension</option>
                  <option value="document_processing_demo">Document Processing Demo (.txt, .pdf)</option>
                  <option value="log_analysis_demo">Log Analysis Demo (.log)</option>
                </select>
              </div>

              <button 
                type="submit" 
                disabled={uploading || !selectedFile}
                className="submit-btn" 
                style={{ 
                  padding: '10px 16px', 
                  fontSize: '0.9rem', 
                  background: 'linear-gradient(135deg, #10b981 0%, #06b6d4 100%)',
                  cursor: uploading || !selectedFile ? 'not-allowed' : 'pointer',
                  opacity: uploading || !selectedFile ? 0.6 : 1,
                  fontWeight: '600',
                  border: 'none',
                  borderRadius: '8px',
                  color: '#fff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px'
                }}
              >
                {uploading ? <RefreshCw className="animate-spin" size={14} /> : <Upload size={14} />}
                {uploading ? 'Uploading...' : 'Ingest & Process File'}
              </button>

              {uploadMessage && (
                <div style={{ 
                  fontSize: '0.8rem', 
                  color: uploadMessage.includes('failed') ? '#ef4444' : '#10b981', 
                  marginTop: '4px',
                  background: uploadMessage.includes('failed') ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.1)',
                  padding: '8px',
                  borderRadius: '6px',
                  border: '1px solid ' + (uploadMessage.includes('failed') ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)')
                }}>
                  {uploadMessage}
                </div>
              )}
            </form>

            {/* List of uploaded files status */}
            {uploadedFiles.length > 0 && (
              <div style={{ marginTop: '16px', borderTop: '1px solid rgba(148, 163, 184, 0.1)', paddingTop: '12px' }}>
                <h4 style={{ fontSize: '0.8rem', fontWeight: '600', color: '#94a3b8', marginBottom: '8px' }}>Recent Ingested Files:</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '160px', overflowY: 'auto' }}>
                  {uploadedFiles.map((f) => (
                    <div 
                      key={f.id} 
                      style={{ 
                        fontSize: '0.75rem', 
                        background: 'rgba(15, 23, 42, 0.4)', 
                        border: '1px solid rgba(148, 163, 184, 0.05)',
                        borderRadius: '6px',
                        padding: '8px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '4px'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: '600', color: '#f1f5f9' }}>
                        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '140px' }}>{f.original_filename}</span>
                        <span style={{ 
                          color: f.status === 'processed' ? '#10b981' : f.status === 'failed' ? '#ef4444' : f.status === 'processing' ? '#3b82f6' : '#94a3b8' 
                        }}>{f.status}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', color: '#64748b', fontSize: '0.7rem' }}>
                        <span>Size: {(f.size_bytes / 1024).toFixed(1)} KB</span>
                        {f.pipeline_id ? (
                          <span 
                            onClick={() => setSelectedPipelineId(f.pipeline_id)}
                            style={{ color: '#a78bfa', cursor: 'pointer', textDecoration: 'underline' }}
                          >
                            Pipeline #{f.pipeline_id}
                          </span>
                        ) : (
                          <span>No pipeline</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Create Pipeline Card */}
          <div style={{ background: 'rgba(15, 23, 42, 0.3)', border: '1px solid rgba(148, 163, 184, 0.1)', borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: '700', marginBottom: '16px', color: '#f1f5f9' }}>Launch New Pipeline</h3>
            <form onSubmit={handleCreatePipeline} className="create-form" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div className="form-field">
                <label style={{ fontSize: '0.75rem' }}>Pipeline Name</label>
                <input 
                  type="text" 
                  value={pipelineName} 
                  onChange={(e) => setPipelineName(e.target.value)} 
                  required 
                  style={{ fontSize: '0.9rem', padding: '10px' }}
                />
              </div>

              <div className="form-field">
                <label style={{ fontSize: '0.75rem' }}>DAG Template Type</label>
                <select 
                  value={pipelineType} 
                  onChange={(e) => handleTypeChange(e.target.value)}
                  style={{ fontSize: '0.9rem', padding: '10px' }}
                >
                  <option value="document_processing_demo">Document Processing Demo (Linear)</option>
                  <option value="log_analysis_demo">Log Analysis Demo (Branching)</option>
                </select>
              </div>

              <div className="form-field">
                <label style={{ fontSize: '0.75rem' }}>Initial Payload (JSON)</label>
                <textarea 
                  value={payloadText} 
                  onChange={(e) => setPayloadText(e.target.value)}
                  rows="4"
                  style={{ 
                    fontFamily: 'monospace', 
                    fontSize: '0.8rem', 
                    background: 'rgba(15, 23, 42, 0.7)', 
                    border: '1px solid rgba(148, 163, 184, 0.2)',
                    borderRadius: '8px',
                    padding: '8px 10px',
                    color: '#94a3b8',
                    resize: 'vertical'
                  }}
                />
              </div>

              <button 
                type="submit" 
                className="submit-btn" 
                style={{ 
                  padding: '10px 16px', 
                  fontSize: '0.9rem', 
                  background: 'linear-gradient(135deg, #ec4899 0%, #8b5cf6 100%)',
                  cursor: 'pointer',
                  fontWeight: '600'
                }}
              >
                Launch Pipeline
              </button>
            </form>
          </div>

          {/* Pipelines Instances List */}
          <div style={{ background: 'rgba(15, 23, 42, 0.3)', border: '1px solid rgba(148, 163, 184, 0.1)', borderRadius: '12px', padding: '20px', flex: 1, minHeight: '300px', display: 'flex', flexDirection: 'column' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: '700', marginBottom: '16px', color: '#f1f5f9' }}>Recent Pipelines</h3>
            
            {pipelines.length === 0 ? (
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '40px 0', color: '#64748b' }}>
                <GitBranch size={32} style={{ opacity: 0.3, marginBottom: '8px' }} />
                <span style={{ fontSize: '0.85rem' }}>No pipelines created yet.</span>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', overflowY: 'auto', maxHeight: '400px', paddingRight: '4px' }}>
                {pipelines.map((p) => {
                  const progress = p.progress || { completed: 0, total: 0 };
                  const percent = progress.total > 0 ? (progress.completed / progress.total) * 100 : 0;
                  const isSelected = selectedPipelineId === p.id;
                  
                  return (
                    <div 
                      key={p.id}
                      onClick={() => setSelectedPipelineId(p.id)}
                      style={{
                        background: isSelected ? 'rgba(139, 92, 246, 0.1)' : 'rgba(30, 41, 59, 0.4)',
                        border: isSelected ? '1px solid rgba(139, 92, 246, 0.4)' : '1px solid rgba(148, 163, 184, 0.1)',
                        borderRadius: '10px',
                        padding: '12px 14px',
                        cursor: 'pointer',
                        transition: 'all 0.2s ease',
                        position: 'relative'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '6px' }}>
                        <div>
                          <div style={{ fontWeight: '700', fontSize: '0.875rem', color: isSelected ? '#a78bfa' : '#f1f5f9', display: 'flex', alignItems: 'center', gap: '6px' }}>
                            #{p.id} {p.name}
                          </div>
                          <span style={{ fontSize: '0.75rem', color: '#64748b', display: 'block', marginTop: '2px' }}>
                            {p.pipeline_type === 'document_processing_demo' ? 'Document Processing' : 'Log Analysis'}
                          </span>
                        </div>
                        
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span className={`badge ${p.status}`} style={{ fontSize: '0.7rem', padding: '2px 8px', borderRadius: '4px', textTransform: 'uppercase', fontWeight: 'bold' }}>
                            {p.status}
                          </span>
                          {(p.status === 'running' || p.status === 'created' || p.status === 'blocked') && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleCancelPipeline(p.id);
                              }}
                              title="Cancel Pipeline"
                              style={{
                                background: 'rgba(239, 68, 68, 0.1)',
                                border: 'none',
                                color: '#ef4444',
                                borderRadius: '4px',
                                padding: '4px',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center'
                              }}
                            >
                              <X size={12} />
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Progress bar */}
                      <div style={{ marginTop: '10px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: '#94a3b8', marginBottom: '4px' }}>
                          <span>Tasks Progress</span>
                          <span>{progress.completed}/{progress.total}</span>
                        </div>
                        <div style={{ width: '100%', height: '5px', background: '#334155', borderRadius: '10px', overflow: 'hidden' }}>
                          <div 
                            style={{ 
                              width: `${percent}%`, 
                              height: '100%', 
                              background: p.status === 'failed' ? '#ef4444' : 'linear-gradient(90deg, #10b981 0%, #34d399 100%)',
                              transition: 'width 0.4s ease'
                            }} 
                          />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

        </div>

        {/* Right Side: Visual Graph & Artifact details */}
        <div style={{ gridColumn: 'span 8', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {selectedPipelineId && selectedPipelineData ? (
            <>
              {/* Pipeline Details Inspector Card */}
              <div style={{ background: 'rgba(30, 41, 59, 0.4)', border: '1px solid rgba(148, 163, 184, 0.1)', borderRadius: '16px', padding: '24px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(148, 163, 184, 0.1)', paddingBottom: '16px', marginBottom: '20px' }}>
                  <div>
                    <h2 style={{ fontSize: '1.2rem', fontWeight: '800', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      Pipeline Instance #{selectedPipelineData.pipeline.id}: {selectedPipelineData.pipeline.name}
                    </h2>
                    <div style={{ display: 'flex', gap: '16px', marginTop: '6px', fontSize: '0.8rem', color: '#94a3b8' }}>
                      <span><strong>Type:</strong> {selectedPipelineData.pipeline.pipeline_type}</span>
                      <span><strong>Launched:</strong> {new Date(selectedPipelineData.pipeline.created_at).toLocaleTimeString()}</span>
                      {selectedPipelineData.pipeline.completed_at && (
                        <span><strong>Finished:</strong> {new Date(selectedPipelineData.pipeline.completed_at).toLocaleTimeString()}</span>
                      )}
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <span className={`badge ${selectedPipelineData.pipeline.status}`} style={{ fontSize: '0.8rem', padding: '4px 12px', borderRadius: '6px', textTransform: 'uppercase', fontWeight: 'bold' }}>
                      {selectedPipelineData.pipeline.status}
                    </span>
                  </div>
                </div>

                {selectedPipelineData.pipeline.error_message && (
                  <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)', color: '#fca5a5', padding: '12px 16px', borderRadius: '8px', marginBottom: '20px', fontSize: '0.85rem' }}>
                    <strong>Pipeline Error:</strong> {selectedPipelineData.pipeline.error_message}
                  </div>
                )}

                {/* Visual DAG Stage-Based Representation */}
                <h4 style={{ fontSize: '0.85rem', textTransform: 'uppercase', color: '#94a3b8', letterSpacing: '0.5px', marginBottom: '16px', fontWeight: '700' }}>
                  DAG Dependency Graph
                </h4>

                <div 
                  style={{ 
                    display: 'flex', 
                    alignItems: 'stretch', 
                    justifyContent: 'space-between',
                    background: '#0f172a', 
                    borderRadius: '12px', 
                    padding: '24px', 
                    overflowX: 'auto',
                    border: '1px solid rgba(148, 163, 184, 0.05)',
                    gap: '12px'
                  }}
                >
                  {stages.map((stageTasks, stageIdx) => (
                    <React.Fragment key={stageIdx}>
                      {stageIdx > 0 && (
                        <div style={{ display: 'flex', alignItems: 'center', color: '#475569', padding: '0 4px' }}>
                          <ChevronRight size={24} />
                        </div>
                      )}
                      
                      {/* Stage Column */}
                      <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: '16px', flex: 1, minWidth: '160px' }}>
                        <div style={{ fontSize: '0.7rem', color: '#64748b', fontWeight: 'bold', textTransform: 'uppercase', textAlign: 'center', borderBottom: '1px solid rgba(148, 163, 184, 0.1)', paddingBottom: '4px', marginBottom: '4px' }}>
                          Stage {stageIdx + 1}
                        </div>
                        
                        {stageTasks.map((t) => (
                          <div 
                            key={t.id} 
                            style={{
                              background: t.status === 'running' ? 'rgba(59, 130, 246, 0.1)' : 'rgba(30, 41, 59, 0.9)',
                              border: t.status === 'running' 
                                ? '1px solid #3b82f6' 
                                : t.status === 'completed'
                                ? '1px solid rgba(16, 185, 129, 0.4)'
                                : t.status === 'failed'
                                ? '1px solid #ef4444'
                                : t.status === 'blocked'
                                ? '1px solid #f59e0b'
                                : '1px solid rgba(148, 163, 184, 0.15)',
                              borderRadius: '8px',
                              padding: '10px 12px',
                              boxShadow: t.status === 'running' ? '0 0 12px rgba(59, 130, 246, 0.15)' : 'none',
                              position: 'relative'
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '6px' }}>
                              <span style={{ fontSize: '0.8rem', fontWeight: 'bold', color: '#f8fafc', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                {t.type.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                              </span>
                              {getStatusIcon(t.status)}
                            </div>
                            
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '6px', fontSize: '0.7rem', color: '#94a3b8' }}>
                              <span>Task #{t.id}</span>
                              <span style={{ 
                                background: t.priority === 'high' ? 'rgba(239, 68, 68, 0.15)' : t.priority === 'medium' ? 'rgba(59, 130, 246, 0.15)' : 'rgba(148, 163, 184, 0.15)',
                                color: t.priority === 'high' ? '#fca5a5' : t.priority === 'medium' ? '#93c5fd' : '#cbd5e1',
                                padding: '1px 4px',
                                borderRadius: '3px',
                                fontSize: '0.65rem'
                              }}>
                                {t.priority}
                              </span>
                            </div>

                            {t.assigned_worker_id && (
                              <div style={{ fontSize: '0.65rem', color: '#64748b', marginTop: '4px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                ⚙ {t.assigned_worker_id}
                              </div>
                            )}

                            {t.blocked_reason && (
                              <div 
                                title={t.blocked_reason}
                                style={{ 
                                  fontSize: '0.65rem', 
                                  color: '#fbbf24', 
                                  marginTop: '4px', 
                                  background: 'rgba(245, 158, 11, 0.1)', 
                                  padding: '2px 4px', 
                                  borderRadius: '4px',
                                  whiteSpace: 'nowrap', 
                                  overflow: 'hidden', 
                                  textOverflow: 'ellipsis' 
                                }}
                              >
                                ⚠ {t.blocked_reason}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </React.Fragment>
                  ))}
                </div>

                {/* Pipeline Artifacts Subsection */}
                <div style={{ marginTop: '24px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                  
                  {/* Left Column: Artifacts List */}
                  <div>
                    <h4 style={{ fontSize: '0.85rem', textTransform: 'uppercase', color: '#94a3b8', letterSpacing: '0.5px', marginBottom: '12px', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <FileText size={16} />
                      Generated Artifacts
                    </h4>
                    
                    {selectedPipelineData.artifacts.length === 0 ? (
                      <div style={{ background: '#0f172a', borderRadius: '8px', padding: '24px', textAlign: 'center', border: '1px solid rgba(148, 163, 184, 0.05)', color: '#64748b', fontSize: '0.8rem' }}>
                        No artifacts registered yet for this pipeline.
                      </div>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxH: '250px', overflowY: 'auto' }}>
                        {selectedPipelineData.artifacts.map((a) => (
                          <div 
                            key={a.id}
                            onClick={() => handleViewArtifact(a)}
                            style={{
                              background: '#0f172a',
                              border: '1px solid rgba(148, 163, 184, 0.1)',
                              borderRadius: '8px',
                              padding: '10px 12px',
                              cursor: 'pointer',
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              transition: 'all 0.2s',
                              hover: { borderColor: '#8b5cf6' }
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.borderColor = '#8b5cf6'}
                            onMouseLeave={(e) => e.currentTarget.style.borderColor = 'rgba(148, 163, 184, 0.1)'}
                          >
                            <div>
                              <div style={{ fontSize: '0.8rem', fontWeight: 'bold', color: '#f1f5f9' }}>
                                {a.artifact_type.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                              </div>
                              <div style={{ fontSize: '0.65rem', color: '#64748b', marginTop: '2px' }}>
                                Task #{a.task_id} • ID #{a.id}
                              </div>
                            </div>
                            <button 
                              style={{ 
                                background: 'rgba(139, 92, 246, 0.1)', 
                                border: 'none', 
                                color: '#a78bfa', 
                                borderRadius: '4px', 
                                padding: '4px 8px', 
                                fontSize: '0.7rem', 
                                cursor: 'pointer',
                                fontWeight: '600'
                              }}
                            >
                              Inspect
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Right Column: Artifact Viewer panel */}
                  <div>
                    <h4 style={{ fontSize: '0.85rem', textTransform: 'uppercase', color: '#94a3b8', letterSpacing: '0.5px', marginBottom: '12px', fontWeight: '700' }}>
                      Artifact Data Inspector
                    </h4>

                    <div 
                      style={{ 
                        background: '#0f172a', 
                        borderRadius: '8px', 
                        padding: '16px', 
                        border: '1px solid rgba(148, 163, 184, 0.05)',
                        minHeight: '200px',
                        maxHeight: '250px',
                        overflowY: 'auto',
                        fontFamily: 'monospace',
                        fontSize: '0.75rem',
                        color: '#cbd5e1'
                      }}
                    >
                      {artifactLoading ? (
                        <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center', color: '#64748b' }}>
                          <RefreshCw className="animate-spin" size={20} />
                          <span style={{ marginLeft: '8px' }}>Loading content from disk...</span>
                        </div>
                      ) : activeArtifact ? (
                        <div>
                          <div style={{ borderBottom: '1px solid rgba(148, 163, 184, 0.1)', paddingBottom: '6px', marginBottom: '8px', color: '#8b5cf6', fontWeight: 'bold' }}>
                            Type: {activeArtifact.artifact_type} (ID: {activeArtifact.id})
                          </div>
                          <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                            {JSON.stringify(activeArtifact.content, null, 2)}
                          </pre>
                        </div>
                      ) : (
                        <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center', color: '#64748b', textAlign: 'center', padding: '20px 0' }}>
                          Select an artifact to inspect its serialized content.
                        </div>
                      )}
                    </div>
                  </div>

                </div>

              </div>
            </>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', flex: 1, border: '2px dashed rgba(148, 163, 184, 0.1)', borderRadius: '16px', padding: '60px', color: '#64748b', minHeight: '400px' }}>
              <GitBranch size={48} style={{ opacity: 0.2, marginBottom: '16px' }} />
              <h3 style={{ fontSize: '1.1rem', fontWeight: '700', color: '#94a3b8', marginBottom: '6px' }}>No Pipeline Selected</h3>
              <p style={{ fontSize: '0.85rem', maxWidth: '380px', textAlign: 'center' }}>
                Launch a demo pipeline on the left or select an existing instance to visualize its DAG nodes, execution states, and filesystem artifacts.
              </p>
            </div>
          )}

        </div>
      </div>

      {/* Integration Test Results Modal */}
      {showTestModal && (
        <div className="modal-overlay" onClick={() => setShowTestModal(false)} style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(15, 23, 42, 0.85)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 1000
        }}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{
            background: '#1e293b',
            border: '1px solid #334155',
            borderRadius: '16px',
            width: '90%',
            maxWidth: '700px',
            maxHeight: '85vh',
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)',
            color: '#f8fafc'
          }}>
            <div className="modal-header" style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '18px 24px',
              borderBottom: '1px solid #334155'
            }}>
              <h2 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{
                  background: testResults?.status === 'success' ? '#10b981' : testResults?.status === 'failed' ? '#ef4444' : '#64748b',
                  color: '#ffffff',
                  padding: '3px 8px',
                  borderRadius: '6px',
                  fontSize: '0.7rem',
                  textTransform: 'uppercase',
                  fontWeight: 'bold'
                }}>
                  {testing ? 'Testing...' : testResults?.status || 'unknown'}
                </span>
                DAG Orchestration Tests
              </h2>
              <button 
                onClick={() => setShowTestModal(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#94a3b8',
                  cursor: 'pointer',
                  fontSize: '1.2rem'
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
              fontSize: '0.85rem',
              lineHeight: 1.6,
              background: '#0f172a'
            }}>
              {testing ? (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '150px', color: '#94a3b8' }}>
                  <RefreshCw className="animate-spin" size={32} />
                  <span style={{ marginTop: '12px' }}>Executing Test A through Test H in real-time...</span>
                </div>
              ) : (
                <>
                  {testResults?.logs && testResults.logs.map((log, index) => {
                    let color = '#cbd5e1';
                    if (log.startsWith('--- Test')) color = '#3b82f6';
                    if (log.includes('successfully') || log.includes('passed') || log.includes('Verified')) color = '#10b981';
                    if (log.includes('Failed') || log.includes('error') || log.includes('stale')) color = '#fca5a5';
                    
                    return (
                      <div key={index} style={{ color, marginBottom: '6px', whiteSpace: 'pre-wrap' }}>
                        {log}
                      </div>
                    );
                  })}
                  
                  {testResults?.error && (
                    <div style={{ color: '#ef4444', marginTop: '12px', padding: '12px', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
                      <strong>Execution Error:</strong> {JSON.stringify(testResults.error, null, 2)}
                    </div>
                  )}
                </>
              )}
            </div>
            
            <div className="modal-footer" style={{
              padding: '16px 24px',
              borderTop: '1px solid #334155',
              display: 'flex',
              justifyContent: 'flex-end'
            }}>
              <button 
                onClick={() => setShowTestModal(false)}
                disabled={testing}
                style={{
                  background: '#334155',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '8px',
                  padding: '8px 20px',
                  fontSize: '0.85rem',
                  fontWeight: '600',
                  cursor: testing ? 'not-allowed' : 'pointer'
                }}
              >
                Close Logs
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PipelineDashboard;
