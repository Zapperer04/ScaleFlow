import React, { useState, useEffect } from 'react';
import { 
  GitBranch, Play, X, RefreshCw, FileText, 
  AlertTriangle, Clock, Activity, Upload,
  Search, Database, Sparkles, Cpu, BookOpen, Gauge, Zap, Server
} from 'lucide-react';
import { 
  fetchPipelines, fetchPipelineDetails, createPipeline, 
  cancelPipeline, runPipelineTests, fetchArtifactContent,
  uploadFile, fetchUploadedFiles,
  searchVectors, fetchVectorStats, createRetrievalPipeline, fetchRetrievalPipelineAnswer,
  fetchPipelineDag, fetchPipelineTimeline,
  getSystemMetrics, getScalingMetrics, getPipelineMetrics, getBackpressureMetrics,
  fetchEvents, fetchPipelineEvents,
  fetchPipelineSnapshots, triggerPipelineSnapshot,
  getClusterStatus, getWorkersRegistry, getClusterFailovers
} from '../services/api';

import ReactFlow, { MiniMap, Controls, Background, Position, Handle } from 'reactflow';
import 'reactflow/dist/style.css';
import dagre from 'dagre';


const DEFAULT_PAYLOADS = {
  document_processing_demo: {
    source_text: "ScaleFlow DAG Orchestration makes distributed workflows extremely reliable and artifact-driven."
  },
  log_analysis_demo: {
    source_text: "2026-05-21 12:00:01 ERROR: Database connection failed after 3 retries\n2026-05-21 12:00:05 WARNING: Redis connection timeout, retrying...\n2026-05-21 12:00:10 INFO: System health check passed"
  }
};

const CustomTaskNode = ({ data }) => {
  const {
    id,
    type,
    status,
    assigned_worker_id,
    retry_count,
    recovered_count,
    lease_renewal_count,
    queue_wait_duration,
    execution_duration,
    input_artifact_ids,
    output_artifact_ids,
    blocked_reason,
  } = data;

  const isOnCriticalPath = data.isOnCriticalPath;
  const isBottleneck = data.isBottleneck;

  let borderColor = '#475569';
  let glowColor = 'rgba(71, 85, 105, 0.1)';

  if (status === 'completed') {
    borderColor = '#10b981';
    glowColor = 'rgba(16, 185, 129, 0.25)';
  } else if (status === 'running') {
    borderColor = '#3b82f6';
    glowColor = 'rgba(59, 130, 246, 0.5)';
  } else if (status === 'failed') {
    borderColor = '#ef4444';
    glowColor = 'rgba(239, 68, 68, 0.4)';
  } else if (status === 'blocked') {
    borderColor = '#f59e0b';
    glowColor = 'rgba(245, 158, 11, 0.4)';
  } else if (status === 'recovering') {
    borderColor = '#8b5cf6';
    glowColor = 'rgba(139, 92, 246, 0.4)';
  }

  // Override if critical path or bottleneck
  if (isOnCriticalPath) {
    borderColor = '#f43f5e'; // Vibrant rose/crimson
    glowColor = 'rgba(244, 63, 94, 0.6)';
  }
  if (isBottleneck) {
    borderColor = '#ef4444'; // Red
    glowColor = 'rgba(239, 68, 68, 0.8)';
  }

  const pulseClass = (status === 'running' || status === 'recovering') ? 'pulse-glow' : '';

  return (
    <div 
      className={`task-node-card ${pulseClass}`}
      style={{
        background: 'var(--bg-panel)',
        border: `2px solid ${borderColor}`,
        borderRadius: '4px',
        padding: '12px',
        color: '#f8fafc',
        width: '240px',
        boxShadow: `0 0 10px ${glowColor}`,
        position: 'relative',
        fontSize: '0.75rem',
        fontFamily: 'system-ui, -apple-system, sans-serif'
      }}
    >
      <Handle type="target" position={Position.Left} style={{ background: borderColor }} />
      
      {isBottleneck && (
        <div style={{
          position: 'absolute',
          top: '-12px',
          left: '10px',
          background: '#ef4444',
          color: '#ffffff',
          padding: '2px 8px',
          borderRadius: '4px',
          fontSize: '0.55rem',
          fontWeight: 'bold',
          border: '1px solid #f8fafc',
          boxShadow: 'none',
          letterSpacing: '0.5px'
        }}>
          ⚠ BOTTLENECK
        </div>
      )}
      {!isBottleneck && isOnCriticalPath && (
        <div style={{
          position: 'absolute',
          top: '-12px',
          left: '10px',
          background: '#f43f5e',
          color: '#ffffff',
          padding: '2px 8px',
          borderRadius: '4px',
          fontSize: '0.55rem',
          fontWeight: 'bold',
          border: '1px solid #f8fafc',
          boxShadow: 'none',
          letterSpacing: '0.5px'
        }}>
          CRITICAL PATH
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
        <span style={{ fontWeight: 'bold', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '140px' }} title={type}>
          {type.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
        </span>
        <span style={{ 
          background: borderColor + '22', 
          color: borderColor, 
          padding: '1px 6px', 
          borderRadius: '4px', 
          fontSize: '0.6rem', 
          fontWeight: 'bold', 
          textTransform: 'uppercase' 
        }}>
          {status}
        </span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', color: '#94a3b8', fontSize: '0.7rem' }}>
        <div><strong>Task ID:</strong> #{id}</div>
        
        {assigned_worker_id ? (
          <div style={{ textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }} title={assigned_worker_id}>
            <strong>Worker:</strong> {assigned_worker_id}
          </div>
        ) : (
          <div style={{ color: '#475569' }}><strong>Worker:</strong> unassigned</div>
        )}
        
        <div>
          <strong>Wait:</strong> {queue_wait_duration}s | <strong>Exec:</strong> {execution_duration}s
        </div>

        {data.weightDetails && (
          <div style={{ 
            borderTop: '1px dashed var(--border-subtle)', 
            paddingTop: '4px', 
            marginTop: '4px', 
            fontSize: '0.65rem', 
            color: '#cbd5e1', 
            display: 'grid', 
            gridTemplateColumns: '1fr 1fr', 
            gap: '4px' 
          }}>
            <div><strong>Dep Wait:</strong> {data.weightDetails.dependency_wait}s</div>
            <div><strong>Q Wait:</strong> {data.weightDetails.queue_wait}s</div>
            <div><strong>Exec:</strong> {data.weightDetails.execution_duration}s</div>
            {data.weightDetails.recovery_delay > 0 && (
              <div style={{ color: '#f87171' }}><strong>Rec Delay:</strong> {data.weightDetails.recovery_delay}s</div>
            )}
          </div>
        )}

        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '2px' }}>
          {retry_count > 0 && (
            <span style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#fca5a5', padding: '1px 4px', borderRadius: '3px', fontSize: '0.65rem' }}>
              Retries: {retry_count}
            </span>
          )}
          {recovered_count > 0 && (
            <span style={{ background: 'rgba(168, 85, 247, 0.15)', color: '#d8b4fe', padding: '1px 4px', borderRadius: '3px', fontSize: '0.65rem' }}>
              Recovered: {recovered_count}
            </span>
          )}
          {lease_renewal_count > 0 && (
            <span style={{ background: 'rgba(59, 130, 246, 0.15)', color: '#93c5fd', padding: '1px 4px', borderRadius: '3px', fontSize: '0.65rem' }}>
              Renewals: {lease_renewal_count}
            </span>
          )}
        </div>

        {((input_artifact_ids && input_artifact_ids.length > 0) || (output_artifact_ids && output_artifact_ids.length > 0)) && (
          <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '4px', marginTop: '4px', fontSize: '0.65rem', display: 'flex', flexDirection: 'column', gap: '2px' }}>
            {input_artifact_ids && input_artifact_ids.length > 0 && (
              <div><strong>Inputs:</strong> {input_artifact_ids.map(aid => `#${aid}`).join(', ')}</div>
            )}
            {output_artifact_ids && output_artifact_ids.length > 0 && (
              <div><strong>Outputs:</strong> {output_artifact_ids.map(aid => `#${aid}`).join(', ')}</div>
            )}
          </div>
        )}

        {blocked_reason && (
          <div style={{ color: '#fbbf24', background: 'rgba(245, 158, 11, 0.1)', padding: '2px 4px', borderRadius: '4px', marginTop: '4px', fontSize: '0.65rem' }}>
            <strong>Blocked:</strong> {blocked_reason}
          </div>
        )}
      </div>

      <Handle type="source" position={Position.Right} style={{ background: borderColor }} />
    </div>
  );
};

const CustomArtifactNode = ({ data }) => {
  const { id, artifact_type } = data;
  return (
    <div 
      style={{
        background: 'var(--bg-primary)',
        border: '1.5px solid #10b981',
        borderRadius: '20px',
        padding: '6px 12px',
        color: '#f8fafc',
        width: '160px',
        textAlign: 'center',
        boxShadow: '0 0 8px rgba(16, 185, 129, 0.2)',
        position: 'relative',
        fontSize: '0.7rem',
        fontFamily: 'system-ui, -apple-system, sans-serif'
      }}
    >
      <Handle type="target" position={Position.Left} style={{ background: '#10b981' }} />
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px' }}>
        <FileText size={12} style={{ color: '#10b981' }} />
        <span style={{ fontWeight: 'bold', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={artifact_type}>
          {artifact_type.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
        </span>
      </div>
      <div style={{ color: '#64748b', fontSize: '0.6rem', marginTop: '2px' }}>
        Artifact #{id}
      </div>
      <Handle type="source" position={Position.Right} style={{ background: '#10b981' }} />
    </div>
  );
};

const nodeTypes = {
  taskNode: CustomTaskNode,
  artifactNode: CustomArtifactNode,
};

const getLayoutedElements = (nodes, edges, direction = 'LR') => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: direction, nodesep: 40, ranksep: 60 });

  nodes.forEach((node) => {
    const width = node.type === 'taskNode' ? 240 : 160;
    const height = node.type === 'taskNode' ? 120 : 70;
    dagreGraph.setNode(node.id, { width, height });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const positionedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    const width = node.type === 'taskNode' ? 240 : 160;
    const height = node.type === 'taskNode' ? 120 : 70;
    
    return {
      ...node,
      targetPosition: direction === 'LR' ? 'left' : 'top',
      sourcePosition: direction === 'LR' ? 'right' : 'bottom',
      position: {
        x: nodeWithPosition.x - width / 2,
        y: nodeWithPosition.y - height / 2,
      },
    };
  });

  return { nodes: positionedNodes, edges };
};

const reconstructStateClient = (events) => {
  const state = {
    pipeline: { status: 'created', started_at: null, completed_at: null, error_message: null },
    tasks: {},
    artifacts: [],
    dependencies: {},
    dependency_releases: {}
  };

  const taskQueuedTimes = {};

  events.forEach((evt) => {
    const type = evt.event_type.toUpperCase();
    const payload = evt.payload_json || {};
    const tid = evt.task_id ? String(evt.task_id) : null;
    const evtTime = evt.created_at;

    if (type === 'PIPELINE_CREATED') {
      state.pipeline.status = 'created';
      state.pipeline.created_at = evtTime;
    } else if (type === 'PIPELINE_COMPLETED') {
      state.pipeline.status = 'completed';
      state.pipeline.completed_at = evtTime;
    } else if (type === 'PIPELINE_FAILED') {
      state.pipeline.status = 'failed';
      state.pipeline.completed_at = evtTime;
      state.pipeline.error_message = payload.error_message;
    } else if (type === 'TASK_CREATED') {
      if (tid) {
        state.tasks[tid] = {
          id: evt.task_id,
          type: payload.task_type || '',
          status: 'pending',
          priority: payload.priority || 'medium',
          retry_count: 0,
          max_retries: 3,
          error_message: null,
          created_at: evtTime,
          started_at: null,
          completed_at: null,
          assigned_worker_id: null,
          lease_token: null,
          lease_expires_at: null,
          recovered_count: 0,
          lease_renewal_count: 0,
          input_artifact_ids: [],
          output_artifact_ids: [],
          blocked_reason: null,
          deferred_at: null,
          queue_wait_duration: 0.0,
          execution_duration: 0.0
        };
        state.dependencies[tid] = payload.dependencies || [];
      }
    } else if (type === 'TASK_QUEUED') {
      if (tid && state.tasks[tid]) {
        state.tasks[tid].status = 'pending';
        taskQueuedTimes[tid] = new Date(evtTime);
      }
    } else if (type === 'TASK_CLAIMED') {
      if (tid && state.tasks[tid]) {
        state.tasks[tid].status = 'running';
        state.tasks[tid].assigned_worker_id = payload.worker_id;
        state.tasks[tid].lease_token = payload.lease_token;
        if (evtTime) {
          const duration = payload.lease_duration || 30;
          const expDate = new Date(new Date(evtTime).getTime() + duration * 1000);
          state.tasks[tid].lease_expires_at = expDate.toISOString();
        }
      }
    } else if (type === 'LEASE_RENEWED') {
      if (tid && state.tasks[tid]) {
        state.tasks[tid].lease_renewal_count += 1;
        if (evtTime) {
          const duration = payload.lease_duration || 30;
          const expDate = new Date(new Date(evtTime).getTime() + duration * 1000);
          state.tasks[tid].lease_expires_at = expDate.toISOString();
        }
      }
    } else if (type === 'LEASE_EXPIRED') {
      if (tid && state.tasks[tid]) {
        state.tasks[tid].status = 'pending';
        state.tasks[tid].lease_token = null;
        state.tasks[tid].assigned_worker_id = null;
      }
    } else if (type === 'TASK_STARTED') {
      if (tid && state.tasks[tid]) {
        state.tasks[tid].status = 'running';
        state.tasks[tid].started_at = evtTime;
        state.tasks[tid].assigned_worker_id = payload.worker_id;
        state.tasks[tid].lease_token = payload.lease_token;
        if (!state.pipeline.started_at) {
          state.pipeline.started_at = evtTime;
          state.pipeline.status = 'running';
        }
        if (taskQueuedTimes[tid] && evtTime) {
          state.tasks[tid].queue_wait_duration = Math.round(
            ((new Date(evtTime) - taskQueuedTimes[tid]) / 1000) * 100
          ) / 100;
        }
      }
    } else if (type === 'TASK_COMPLETED') {
      if (tid && state.tasks[tid]) {
        state.tasks[tid].status = 'completed';
        state.tasks[tid].completed_at = evtTime;
        if (state.tasks[tid].started_at && evtTime) {
          state.tasks[tid].execution_duration = Math.round(
            ((new Date(evtTime) - new Date(state.tasks[tid].started_at)) / 1000) * 100
          ) / 100;
        }
        state.tasks[tid].output_artifact_ids = payload.output_artifact_ids || [];
      }
    } else if (type === 'TASK_FAILED') {
      if (tid && state.tasks[tid]) {
        state.tasks[tid].status = 'failed';
        state.tasks[tid].error_message = payload.error_message;
        state.tasks[tid].retry_count += 1;
      }
    } else if (type === 'TASK_RECOVERED') {
      if (tid && state.tasks[tid]) {
        state.tasks[tid].status = 'pending';
        state.tasks[tid].recovered_count = payload.recovered_count || (state.tasks[tid].recovered_count + 1);
        state.tasks[tid].lease_token = null;
        state.tasks[tid].assigned_worker_id = null;
        if (state.pipeline.status === 'running') {
          state.pipeline.status = 'recovering';
        }
      }
    } else if (type === 'TASK_BLOCKED' || type === 'DEPENDENCY_BLOCKED') {
      if (tid && state.tasks[tid]) {
        state.tasks[tid].status = 'blocked';
        state.tasks[tid].blocked_reason = payload.blocked_reason;
      }
    } else if (type === 'TASK_RELEASED' || type === 'DEPENDENCY_RELEASED') {
      if (tid && state.tasks[tid]) {
        state.tasks[tid].status = 'pending';
        state.tasks[tid].blocked_reason = null;
      }
    } else if (type === 'BACKPRESSURE_DEFERRED') {
      if (tid && state.tasks[tid]) {
        state.tasks[tid].status = 'deferred';
        state.tasks[tid].deferred_at = evtTime;
      }
    } else if (type === 'PRIORITY_ESCALATED') {
      if (tid && state.tasks[tid]) {
        state.tasks[tid].priority = payload.new_priority || 'medium';
      }
    } else if (type === 'ARTIFACT_CREATED') {
      const art = {
        id: payload.artifact_id,
        pipeline_id: evt.pipeline_id,
        task_id: evt.task_id,
        artifact_type: payload.artifact_type,
        storage_uri: payload.storage_uri,
        created_at: evtTime
      };
      state.artifacts.push(art);
      if (tid && state.tasks[tid]) {
        const artId = payload.artifact_id;
        if (!state.tasks[tid].output_artifact_ids.includes(artId)) {
          state.tasks[tid].output_artifact_ids.push(artId);
        }
      }
    } else if (type === 'DEPENDENCY_RELEASED') {
      const p = String(payload.parent_task_id);
      const c = String(payload.child_task_id);
      if (!state.dependency_releases[c]) state.dependency_releases[c] = {};
      state.dependency_releases[c][p] = true;
    } else if (type === 'DEPENDENCY_BLOCKED') {
      const p = String(payload.parent_task_id);
      const c = String(payload.child_task_id);
      if (!state.dependency_releases[c]) state.dependency_releases[c] = {};
      state.dependency_releases[c][p] = false;
    }
  });

  return state;
};

const PipelineDashboard = () => {
  const [pipelines, setPipelines] = useState([]);
  const [selectedPipelineId, setSelectedPipelineId] = useState(null);
  const [selectedPipelineData, setSelectedPipelineData] = useState(null);
  const selectedPipelineDataRef = React.useRef(null);
  useEffect(() => {
    selectedPipelineDataRef.current = selectedPipelineData;
  }, [selectedPipelineData]);
  const [pipelineType, setPipelineType] = useState('document_processing_demo');
  const [pipelineName, setPipelineName] = useState('Demo Document Pipeline');
  const [payloadText, setPayloadText] = useState(JSON.stringify(DEFAULT_PAYLOADS.document_processing_demo, null, 2));
  
  // Systems Observability & Backpressure States
  const [dashboardTab, setDashboardTab] = useState('orchestration');
  const [pipelineMetrics, setPipelineMetrics] = useState(null);
  const [systemMetricsData, setSystemMetricsData] = useState(null);
  const [scalingData, setScalingData] = useState(null);
  const [backpressureData, setBackpressureData] = useState(null);

  // Phase 8 HA Observability States
  const [clusterStatus, setClusterStatus] = useState(null);
  const [workersRegistry, setWorkersRegistry] = useState([]);
  const [clusterFailovers, setClusterFailovers] = useState([]);

  // Event Sourcing & Replay States
  const [globalEvents, setGlobalEvents] = useState([]);
  const [globalEventCategory, setGlobalEventCategory] = useState('');
  const [replayPipelineId, setReplayPipelineId] = useState(null);
  const [replayEvents, setReplayEvents] = useState([]);
  const [replaySnapshots, setReplaySnapshots] = useState([]);
  const [replayScrubberVal, setReplayScrubberVal] = useState(0);
  const [replayStatus, setReplayStatus] = useState('paused');
  const [replaySpeed, setReplaySpeed] = useState(1.0);
  const [replayNodes, setReplayNodes] = useState([]);
  const [replayEdges, setReplayEdges] = useState([]);
  const [originalReplayDag, setOriginalReplayDag] = useState(null);

  const loadSystemObservabilityData = async () => {
    try {
      const [sys, scale, bp, cluster, registry, failovers] = await Promise.all([
        getSystemMetrics(),
        getScalingMetrics(),
        getBackpressureMetrics(),
        getClusterStatus(),
        getWorkersRegistry(),
        getClusterFailovers()
      ]);
      setSystemMetricsData(sys);
      setScalingData(scale);
      setBackpressureData(bp);
      setClusterStatus(cluster);
      setWorkersRegistry(registry || []);
      setClusterFailovers(failovers || []);
    } catch (err) {
      console.error('Failed to load system observability metrics:', err);
    }
  };

  // React Flow states
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  
  // Timeline states
  const [activeTab, setActiveTab] = useState('artifacts');
  const [pipelineTimeline, setPipelineTimeline] = useState([]);
  const [timelineFilter, setTimelineFilter] = useState('all');
  const [timelineSearch, setTimelineSearch] = useState('');

  
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

  // Semantic Search & Vector Stats State
  const [searchQuery, setSearchQuery] = useState('');
  const [topK, setTopK] = useState(5);
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [searchFilterPipeline, setSearchFilterPipeline] = useState('');
  const [vectorStats, setVectorStats] = useState(null);

  // Retrieval Pipeline State
  const [retrievalQuery, setRetrievalQuery] = useState('');
  const [retrievalTopK, setRetrievalTopK] = useState(5);
  const [retrievalPipelineFilter, setRetrievalPipelineFilter] = useState('');
  const [retrievalFileFilter, setRetrievalFileFilter] = useState('');
  const [retrievalRunning, setRetrievalRunning] = useState(false);
  const [createdQueryPipelineId, setCreatedQueryPipelineId] = useState(null);
  const [retrievalPipelineProgress, setRetrievalPipelineProgress] = useState(null);
  const [retrievalAnswer, setRetrievalAnswer] = useState(null);

  const handleRunRetrievalPipeline = async (e) => {
    e.preventDefault();
    if (!retrievalQuery) return;
    setRetrievalRunning(true);
    setCreatedQueryPipelineId(null);
    setRetrievalPipelineProgress(null);
    setRetrievalAnswer(null);
    
    try {
      const payload = {
        query: retrievalQuery,
        top_k: retrievalTopK,
      };
      if (retrievalPipelineFilter) {
        payload.pipeline_id_filter = parseInt(retrievalPipelineFilter);
      }
      if (retrievalFileFilter) {
        payload.file_id_filter = parseInt(retrievalFileFilter);
      }
      
      const res = await createRetrievalPipeline(payload);
      setCreatedQueryPipelineId(res.pipeline_id);
      setRetrievalPipelineProgress(res);
      setSelectedPipelineId(res.pipeline_id);
    } catch (err) {
      console.error('Failed to start retrieval pipeline:', err);
      alert('Failed to start retrieval pipeline: ' + (err.response?.data?.error || err.message));
      setRetrievalRunning(false);
    }
  };

  // Poll query pipeline answer/progress
  useEffect(() => {
    if (!createdQueryPipelineId) return;
    
    let isMounted = true;
    const pollInterval = setInterval(async () => {
      try {
        const data = await fetchRetrievalPipelineAnswer(createdQueryPipelineId);
        if (!isMounted) return;
        
        setRetrievalAnswer(data);
        
        try {
          const detail = await fetchPipelineDetails(createdQueryPipelineId);
          if (isMounted) {
            setRetrievalPipelineProgress(detail);
            if (detail.status === 'completed' || detail.status === 'failed') {
              setRetrievalRunning(false);
              clearInterval(pollInterval);
            }
          }
        } catch (taskErr) {
          console.error('Failed to poll retrieval tasks details:', taskErr);
        }
        
      } catch (err) {
        console.error('Failed to poll retrieval answer:', err);
      }
    }, 2000);
    
    return () => {
      isMounted = false;
      clearInterval(pollInterval);
    };
  }, [createdQueryPipelineId]);


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

  // Sync selected pipeline DAG
  const loadPipelineDag = async (id) => {
    try {
      const data = await fetchPipelineDag(id);
      let metrics = null;
      try {
        metrics = await getPipelineMetrics(id);
        setPipelineMetrics(metrics);
      } catch (err) {
        console.error('Failed to load pipeline metrics:', err);
      }

      if (data && data.nodes && data.edges) {
        // Pre-process nodes with critical path and bottleneck flags
        const criticalNodeIds = metrics && metrics.critical_path 
          ? metrics.critical_path.map(tid => `task-${tid}`) 
          : [];
        const bottleneckNodeId = metrics && metrics.bottleneck_node_id 
          ? `task-${metrics.bottleneck_node_id}` 
          : null;

        const updatedNodes = data.nodes.map(node => {
          const isOnCriticalPath = criticalNodeIds.includes(node.id);
          const isBottleneck = node.id === bottleneckNodeId;
          
          // Inject wait/execution details if present in metrics node_weights
          let weightDetails = null;
          if (node.type === 'taskNode' && metrics && metrics.node_weights) {
            const taskId = node.id.replace('task-', '');
            weightDetails = metrics.node_weights[taskId] || null;
          }

          return {
            ...node,
            data: {
              ...node.data,
              isOnCriticalPath,
              isBottleneck,
              weightDetails
            }
          };
        });

        // Highlight critical path edges and congested edges
        const updatedEdges = data.edges.map(edge => {
          // Check if target is throttled due to upstream congestion
          const targetNode = data.nodes.find(n => n.id === edge.target);
          const isTargetThrottled = targetNode && targetNode.type === 'taskNode' && 
            targetNode.data?.status === 'blocked' && 
            targetNode.data?.blocked_reason === 'Upstream congestion: throttled';
          
          if (isTargetThrottled) {
            return {
              ...edge,
              animated: true,
              style: {
                stroke: '#f87171', // Dotted light-red
                strokeDasharray: '5,5',
                strokeWidth: 2.5
              }
            };
          }

          let isCriticalEdge = false;
          
          if (metrics && metrics.critical_path) {

            if (edge.source.startsWith('task-') && edge.target.startsWith('task-')) {
              const srcId = parseInt(edge.source.replace('task-', ''));
              const tgtId = parseInt(edge.target.replace('task-', ''));
              const srcIdx = metrics.critical_path.indexOf(srcId);
              const tgtIdx = metrics.critical_path.indexOf(tgtId);
              isCriticalEdge = srcIdx !== -1 && tgtIdx !== -1 && (srcIdx + 1 === tgtIdx || tgtIdx + 1 === srcIdx);
            } else if (edge.source.startsWith('task-') && edge.target.startsWith('artifact-')) {
              const srcId = parseInt(edge.source.replace('task-', ''));
              const artNode = data.nodes.find(n => n.id === edge.target);
              const isSourceInPath = metrics.critical_path.includes(srcId);
              isCriticalEdge = isSourceInPath && artNode && artNode.data.task_id === srcId;
            } else if (edge.source.startsWith('artifact-') && edge.target.startsWith('task-')) {
              const tgtId = parseInt(edge.target.replace('task-', ''));
              const artNode = data.nodes.find(n => n.id === edge.source);
              const isTargetInPath = metrics.critical_path.includes(tgtId);
              const parentId = artNode ? artNode.data.task_id : null;
              isCriticalEdge = isTargetInPath && parentId && metrics.critical_path.includes(parentId) && metrics.critical_path.indexOf(parentId) < metrics.critical_path.indexOf(tgtId);
            }
          }

          if (isCriticalEdge) {
            return {
              ...edge,
              animated: true,
              style: {
                stroke: '#f43f5e', // Vibrant rose/crimson
                strokeWidth: 3.5
              }
            };
          }
          return edge;
        });

        const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
          updatedNodes,
          updatedEdges,
          'LR'
        );
        setNodes(layoutedNodes);
        setEdges(layoutedEdges);
      }
    } catch (err) {
      console.error('Failed to load pipeline DAG:', err);
    }
  };

  // Sync selected pipeline timeline
  const loadPipelineTimeline = async (id) => {
    try {
      const data = await fetchPipelineTimeline(id);
      setPipelineTimeline(data || []);
    } catch (err) {
      console.error('Failed to load pipeline timeline:', err);
    }
  };

  // Sync selected pipeline details
  const loadPipelineDetails = async (id) => {
    try {
      const data = await fetchPipelineDetails(id);
      setSelectedPipelineData(data);
      // Simultaneously fetch DAG and Timeline
      await loadPipelineDag(id);
      await loadPipelineTimeline(id);
    } catch (err) {
      console.error('Failed to load pipeline details:', err);
    }
  };

  // Sync vector stats
  const loadVectorStatsData = async () => {
    try {
      const stats = await fetchVectorStats();
      setVectorStats(stats);
    } catch (err) {
      console.error('Failed to load vector stats:', err);
    }
  };

  // Event Sourcing & Replay Handlers
  const loadGlobalEvents = async () => {
    try {
      const data = await fetchEvents(globalEventCategory);
      setGlobalEvents(data);
    } catch (err) {
      console.error('Failed to load global events:', err);
    }
  };

  const loadPipelineReplayData = async (pipelineId) => {
    if (!pipelineId) return;
    try {
      const [events, snapshots, dag] = await Promise.all([
        fetchPipelineEvents(pipelineId),
        fetchPipelineSnapshots(pipelineId),
        fetchPipelineDag(pipelineId)
      ]);
      
      setReplayEvents(events);
      setReplaySnapshots(snapshots);
      setOriginalReplayDag(dag);
      setReplayScrubberVal(events.length);
      
      reconstructReplayStateAtStep(events, dag, events.length);
    } catch (err) {
      console.error('Failed to load pipeline replay data:', err);
    }
  };

  const reconstructReplayStateAtStep = (events, dag, stepIndex) => {
    if (!dag || !dag.nodes || !dag.edges) return;
    
    const activeEvents = events.slice(0, stepIndex);
    const reconstructed = reconstructStateClient(activeEvents);
    
    const updatedNodes = dag.nodes.map(node => {
      if (node.type === 'taskNode') {
        const taskId = node.id.replace('task-', '');
        const recTask = reconstructed.tasks[taskId];
        if (recTask) {
          return {
            ...node,
            data: {
              ...node.data,
              status: recTask.status,
              retry_count: recTask.retry_count,
              recovered_count: recTask.recovered_count,
              lease_renewal_count: recTask.lease_renewal_count,
              assigned_worker_id: recTask.assigned_worker_id,
              queue_wait_duration: recTask.queue_wait_duration,
              execution_duration: recTask.execution_duration,
              blocked_reason: recTask.blocked_reason,
            }
          };
        } else {
          return {
            ...node,
            data: {
              ...node.data,
              status: 'pending',
              retry_count: 0,
              recovered_count: 0,
              lease_renewal_count: 0,
              assigned_worker_id: null,
              queue_wait_duration: 0.0,
              execution_duration: 0.0,
              blocked_reason: null
            }
          };
        }
      } else if (node.type === 'artifactNode') {
        const artId = node.data.id;
        const exists = reconstructed.artifacts.some(a => a.id === artId);
        return {
          ...node,
          style: {
            ...node.style,
            opacity: exists ? 1 : 0.3,
            transition: 'opacity 0.3s ease'
          }
        };
      }
      return node;
    });

    const updatedEdges = dag.edges.map(edge => {
      // Check if target is throttled due to upstream congestion in reconstructed state
      const tgtNode = dag.nodes.find(n => n.id === edge.target);
      const tgtTaskId = tgtNode && tgtNode.type === 'taskNode' ? tgtNode.id.replace('task-', '') : null;
      const isTgtThrottled = tgtTaskId && reconstructed.tasks[tgtTaskId] && 
        reconstructed.tasks[tgtTaskId].status === 'blocked' && 
        reconstructed.tasks[tgtTaskId].blocked_reason === 'Upstream congestion: throttled';
      
      if (isTgtThrottled) {
        return {
          ...edge,
          animated: true,
          style: {
            stroke: '#f87171', // Dotted light-red
            strokeDasharray: '5,5',
            strokeWidth: 2.5
          }
        };
      }

      let isCompletedEdge = false;
      if (edge.source.startsWith('task-')) {
        const srcId = edge.source.replace('task-', '');
        if (reconstructed.tasks[srcId] && reconstructed.tasks[srcId].status === 'completed') {
          isCompletedEdge = true;
        }
      }
      
      return {
        ...edge,
        animated: isCompletedEdge,
        style: {
          ...edge.style,
          stroke: isCompletedEdge ? '#10b981' : '#475569',
          strokeWidth: isCompletedEdge ? 2.5 : 1.5
        }
      };
    });

    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
      updatedNodes,
      updatedEdges,
      'LR'
    );
    setReplayNodes(layoutedNodes);
    setReplayEdges(layoutedEdges);
  };

  // Replay Autoplay Effect
  useEffect(() => {
    if (replayStatus !== 'playing' || replayEvents.length === 0) return;
    
    const intervalTime = 1000 / replaySpeed;
    const interval = setInterval(() => {
      setReplayScrubberVal(prev => {
        const next = prev + 1;
        if (next >= replayEvents.length) {
          setReplayStatus('paused');
          clearInterval(interval);
          return replayEvents.length;
        }
        return next;
      });
    }, intervalTime);
    
    return () => clearInterval(interval);
  }, [replayStatus, replaySpeed, replayEvents]);

  // Synchronize timeline scrubbing with graph updates
  useEffect(() => {
    if (replayEvents.length > 0 && originalReplayDag) {
      reconstructReplayStateAtStep(replayEvents, originalReplayDag, replayScrubberVal);
    }
  }, [replayScrubberVal, originalReplayDag, replayEvents]);

  // Periodically poll events for live pipeline replay updates and global feed
  useEffect(() => {
    if (dashboardTab === 'replay') {
      loadGlobalEvents();
      if (replayPipelineId) {
        fetchPipelineEvents(replayPipelineId).then(events => {
          setReplayEvents(events);
          fetchPipelineSnapshots(replayPipelineId).then(snaps => setReplaySnapshots(snaps));
        }).catch(err => console.error(err));
      }
    }
    const interval = setInterval(() => {
      if (dashboardTab === 'replay') {
        loadGlobalEvents();
        if (replayPipelineId && replayStatus === 'paused') {
          fetchPipelineEvents(replayPipelineId).then(events => {
            setReplayEvents(events);
          });
        }
      }
    }, 2000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dashboardTab, replayPipelineId, replayStatus, globalEventCategory]);

  useEffect(() => {
    loadPipelinesList();
    loadUploadedFilesList();
    loadVectorStatsData();
    if (selectedPipelineId) {
      loadPipelineDetails(selectedPipelineId);
    }
    if (dashboardTab === 'observability') {
      loadSystemObservabilityData();
    }
    const interval = setInterval(() => {
      loadPipelinesList();
      loadUploadedFilesList();
      loadVectorStatsData();
      if (selectedPipelineId) {
        const currentData = selectedPipelineDataRef.current;
        const isTerminal = currentData && currentData.pipeline && 
          ['completed', 'failed', 'cancelled'].includes(currentData.pipeline.status);
        if (!isTerminal) {
          loadPipelineDetails(selectedPipelineId);
        }
      }
      if (dashboardTab === 'observability') {
        loadSystemObservabilityData();
      }
    }, 2000); // 2-second polling refresh
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPipelineId, dashboardTab]);


  const handleSearch = async (e) => {
    if (e) e.preventDefault();
    if (!searchQuery) return;
    setSearching(true);
    try {
      const pId = (searchFilterPipeline && searchFilterPipeline !== 'all') ? parseInt(searchFilterPipeline) : null;
      const res = await searchVectors(searchQuery, topK, pId, null);
      setSearchResults(res);
    } catch (err) {
      console.error('Vector search failed:', err);
      alert('Search failed: ' + (err.response?.data?.error || err.message));
    } finally {
      setSearching(false);
    }
  };

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



  return (
    <div className="panel execution-log" style={{ gridColumn: 'span 12', marginTop: '24px' }}>
      
      {/* Dashboard Top Tabs */}
      <div style={{ display: 'flex', gap: '16px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '10px', marginBottom: '20px' }}>
        <button
          onClick={() => setDashboardTab('orchestration')}
          style={{
            background: 'none',
            border: 'none',
            color: dashboardTab === 'orchestration' ? '#8b5cf6' : '#94a3b8',
            fontSize: '1rem',
            fontWeight: 'bold',
            cursor: 'pointer',
            borderBottom: dashboardTab === 'orchestration' ? '2.5px solid #8b5cf6' : 'none',
            paddingBottom: '6px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <GitBranch size={18} />
          DAG Orchestration
        </button>
        <button
          onClick={() => setDashboardTab('observability')}
          style={{
            background: 'none',
            border: 'none',
            color: dashboardTab === 'observability' ? '#8b5cf6' : '#94a3b8',
            fontSize: '1rem',
            fontWeight: 'bold',
            cursor: 'pointer',
            borderBottom: dashboardTab === 'observability' ? '2.5px solid #8b5cf6' : 'none',
            paddingBottom: '6px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <Activity size={18} />
          Systems Observability
        </button>
        <button
          onClick={() => setDashboardTab('replay')}
          style={{
            background: 'none',
            border: 'none',
            color: dashboardTab === 'replay' ? '#8b5cf6' : '#94a3b8',
            fontSize: '1rem',
            fontWeight: 'bold',
            cursor: 'pointer',
            borderBottom: dashboardTab === 'replay' ? '2.5px solid #8b5cf6' : 'none',
            paddingBottom: '6px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <RefreshCw size={18} />
          Replay Engine
        </button>
      </div>

      {dashboardTab === 'orchestration' && (
        <>
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
                background: 'var(--color-accent)',
                color: '#ffffff',
                border: 'none',
                borderRadius: '4px',
                padding: '8px 18px',
                fontSize: '0.85rem',
                fontWeight: '600',
                cursor: testing ? 'not-allowed' : 'pointer',
                boxShadow: 'none',
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
          <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '4px', padding: '20px' }}>
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
                    background: 'rgba(0, 0, 0, 0.2)', 
                    border: '1px dashed var(--border-subtle)',
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
                  background: 'var(--color-accent)',
                  cursor: uploading || !selectedFile ? 'not-allowed' : 'pointer',
                  opacity: uploading || !selectedFile ? 0.6 : 1,
                  fontWeight: '600',
                  border: 'none',
                  borderRadius: '4px',
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
              <div style={{ marginTop: '16px', borderTop: '1px solid var(--border-subtle)', paddingTop: '12px' }}>
                <h4 style={{ fontSize: '0.8rem', fontWeight: '600', color: '#94a3b8', marginBottom: '8px' }}>Recent Ingested Files:</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '160px', overflowY: 'auto' }}>
                  {uploadedFiles.map((f) => (
                    <div 
                      key={f.id} 
                      style={{ 
                        fontSize: '0.75rem', 
                        background: 'var(--bg-panel)', 
                        border: '1px solid var(--border-subtle)',
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
          <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '4px', padding: '20px' }}>
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
                    background: 'rgba(0, 0, 0, 0.3)', 
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '4px',
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
                  background: 'var(--color-accent)',
                  cursor: 'pointer',
                  fontWeight: '600'
                }}
              >
                Launch Pipeline
              </button>
            </form>
          </div>

          {/* Pipelines Instances List */}
          <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '4px', padding: '20px', flex: 1, minHeight: '300px', display: 'flex', flexDirection: 'column' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: '700', marginBottom: '16px', color: '#f1f5f9' }}>Recent Pipelines</h3>
            
            {pipelines.length === 0 ? (
              <div className="empty-state-container" style={{ flex: 1, minHeight: '200px' }}>
                <GitBranch size={36} className="empty-state-icon" />
                <div className="empty-state-title">No pipelines created yet</div>
                <div className="empty-state-text">Start a workflow instance from the configuration panel to track it.</div>
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
                        background: isSelected ? 'rgba(139, 92, 246, 0.1)' : 'var(--bg-panel)',
                        border: isSelected ? '1px solid rgba(139, 92, 246, 0.4)' : '1px solid var(--border-subtle)',
                        borderRadius: '4px',
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
                        <div style={{ width: '100%', height: '5px', background: '#334155', borderRadius: '4px', overflow: 'hidden' }}>
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
              <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '4px', padding: '24px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '16px', marginBottom: '20px' }}>
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
                  <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)', color: '#fca5a5', padding: '12px 16px', borderRadius: '4px', marginBottom: '20px', fontSize: '0.85rem' }}>
                    <strong>Pipeline Error:</strong> {selectedPipelineData.pipeline.error_message}
                  </div>
                )}

                {pipelineMetrics && (
                  <div style={{ background: 'rgba(239, 68, 68, 0.05)', border: '1px solid rgba(239, 68, 68, 0.15)', borderRadius: '4px', padding: '14px', marginBottom: '20px', fontSize: '0.8rem' }}>
                    <h4 style={{ margin: 0, color: '#f43f5e', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                      <AlertTriangle size={14} /> Orchestration Bottleneck Analysis
                    </h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', color: '#cbd5e1' }}>
                      <div><strong>Total Orchestration Latency:</strong> {pipelineMetrics.total_latency_seconds}s</div>
                      <div><strong>Orchestration Overhead:</strong> {pipelineMetrics.orchestration_overhead_seconds}s</div>
                      <div><strong>Slowest Stage:</strong> <span style={{ color: '#ef4444', fontWeight: 'bold' }}>{pipelineMetrics.slowest_stage}</span> (Task #{pipelineMetrics.bottleneck_node_id})</div>
                    </div>
                  </div>
                )}

                {/* Visual DAG Representation */}
                <h4 style={{ fontSize: '0.85rem', textTransform: 'uppercase', color: '#94a3b8', letterSpacing: '0.5px', marginBottom: '16px', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <GitBranch size={16} />
                  DAG Dependency Graph (React Flow)
                </h4>

                <div 
                  style={{ 
                    height: '420px',
                    background: '#090d16', 
                    borderRadius: '4px', 
                    border: '1px solid var(--border-subtle)',
                    position: 'relative',
                    overflow: 'hidden',
                    marginBottom: '20px',
                    boxShadow: 'none'
                  }}
                >
                  <ReactFlow
                    nodes={nodes}
                    edges={edges}
                    nodeTypes={nodeTypes}
                    fitView
                    fitViewOptions={{ padding: 0.15 }}
                    minZoom={0.05}
                    maxZoom={1.5}
                  >
                    <Background color="#334155" gap={16} size={1} />
                    <Controls showInteractive={false} />
                    <MiniMap 
                      nodeColor={(n) => {
                        if (n.type === 'artifactNode') return '#10b981';
                        const status = n.data?.status;
                        if (status === 'completed') return '#10b981';
                        if (status === 'running') return '#3b82f6';
                        if (status === 'failed') return '#ef4444';
                        if (status === 'blocked') return '#f59e0b';
                        if (status === 'recovering') return '#8b5cf6';
                        return '#64748b';
                      }}
                      maskColor='rgba(0, 0, 0, 0.25)'
                      style={{
                        background: '#1e293b',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: '6px'
                      }}
                    />
                  </ReactFlow>
                </div>

                {/* Tab buttons */}
                <div style={{ display: 'flex', gap: '16px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '10px', marginTop: '24px', marginBottom: '16px' }}>
                  <button
                    onClick={() => setActiveTab('artifacts')}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: activeTab === 'artifacts' ? '#8b5cf6' : '#94a3b8',
                      fontSize: '0.9rem',
                      fontWeight: 'bold',
                      cursor: 'pointer',
                      borderBottom: activeTab === 'artifacts' ? '2px solid #8b5cf6' : 'none',
                      paddingBottom: '6px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px'
                    }}
                  >
                    <FileText size={16} />
                    Artifacts Flow
                  </button>
                  <button
                    onClick={() => setActiveTab('timeline')}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: activeTab === 'timeline' ? '#8b5cf6' : '#94a3b8',
                      fontSize: '0.9rem',
                      fontWeight: 'bold',
                      cursor: 'pointer',
                      borderBottom: activeTab === 'timeline' ? '2px solid #8b5cf6' : 'none',
                      paddingBottom: '6px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px'
                    }}
                  >
                    <Clock size={16} />
                    Audit Timeline
                  </button>
                </div>

                {activeTab === 'artifacts' && (
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                    
                    {/* Left Column: Artifacts List */}
                    <div>
                      <h4 style={{ fontSize: '0.85rem', textTransform: 'uppercase', color: '#94a3b8', letterSpacing: '0.5px', marginBottom: '12px', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <FileText size={16} />
                        Generated Artifacts
                      </h4>
                      
                      {selectedPipelineData.artifacts.length === 0 ? (
                        <div style={{ background: '#0f172a', borderRadius: '4px', padding: '24px', textAlign: 'center', border: '1px solid var(--border-subtle)', color: '#64748b', fontSize: '0.8rem' }}>
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
                                border: '1px solid var(--border-subtle)',
                                borderRadius: '4px',
                                padding: '10px 12px',
                                cursor: 'pointer',
                                display: 'flex',
                                justifyStyle: 'space-between',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                transition: 'all 0.2s',
                              }}
                              onMouseEnter={(e) => e.currentTarget.style.borderColor = '#8b5cf6'}
                              onMouseLeave={(e) => e.currentTarget.style.borderColor = 'var(--border-subtle)'}
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
                          background: 'var(--bg-primary)', 
                          borderRadius: '4px', 
                          padding: '16px', 
                          border: '1px solid var(--border-subtle)',
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
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '6px', marginBottom: '8px' }}>
                              <span style={{ color: 'var(--color-accent)', fontWeight: 'bold' }}>
                                Type: {activeArtifact.artifact_type} (ID: {activeArtifact.id})
                              </span>
                              <button 
                                onClick={() => {
                                  navigator.clipboard.writeText(JSON.stringify(activeArtifact.content, null, 2));
                                  alert('Copied artifact JSON to clipboard!');
                                }}
                                style={{
                                  background: 'var(--border-subtle)',
                                  border: '1px solid var(--border-subtle)',
                                  color: '#cbd5e1',
                                  fontSize: '0.65rem',
                                  padding: '2px 8px',
                                  borderRadius: '4px',
                                  cursor: 'pointer',
                                  transition: 'all 0.15s'
                                }}
                                onMouseEnter={(e) => {
                                  e.target.style.background = 'var(--border-subtle)';
                                  e.target.style.color = '#fff';
                                }}
                                onMouseLeave={(e) => {
                                  e.target.style.background = 'var(--border-subtle)';
                                  e.target.style.color = '#cbd5e1';
                                }}
                              >
                                Copy JSON
                              </button>
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
                )}

                {activeTab === 'timeline' && (
                  <div style={{ background: '#0f172a', borderRadius: '4px', padding: '20px', border: '1px solid var(--border-subtle)' }}>
                    {/* Filter and Search controls */}
                    <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '16px', borderBottom: '1px dashed var(--border-subtle)', paddingBottom: '12px' }}>
                      <div style={{ flex: 1, minWidth: '200px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        <label style={{ fontSize: '0.7rem', color: '#64748b', fontWeight: 'bold', textTransform: 'uppercase' }}>Filter Search</label>
                        <input 
                          type="text" 
                          value={timelineSearch}
                          onChange={(e) => setTimelineSearch(e.target.value)}
                          placeholder="Search worker ID, task type, message, task ID..."
                          style={{
                            padding: '8px 12px',
                            fontSize: '0.8rem',
                            background: 'rgba(0, 0, 0, 0.25)',
                            border: '1px solid var(--border-subtle)',
                            borderRadius: '6px',
                            color: '#cbd5e1'
                          }}
                        />
                      </div>

                      <div style={{ width: '180px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        <label style={{ fontSize: '0.7rem', color: '#64748b', fontWeight: 'bold', textTransform: 'uppercase' }}>Event Filter</label>
                        <select 
                          value={timelineFilter}
                          onChange={(e) => setTimelineFilter(e.target.value)}
                          style={{
                            padding: '8px',
                            fontSize: '0.8rem',
                            background: 'rgba(0, 0, 0, 0.25)',
                            border: '1px solid var(--border-subtle)',
                            borderRadius: '6px',
                            color: '#cbd5e1'
                          }}
                        >
                          <option value="all">All Event Types</option>
                          <option value="task_created">task_created</option>
                          <option value="task_queued">task_queued</option>
                          <option value="task_claimed">task_claimed</option>
                          <option value="lease_renewed">lease_renewed</option>
                          <option value="lease_expired">lease_expired</option>
                          <option value="task_started">task_started</option>
                          <option value="task_completed">task_completed</option>
                          <option value="task_failed">task_failed</option>
                          <option value="task_recovered">task_recovered</option>
                          <option value="artifact_created">artifact_created</option>
                          <option value="dependency_released">dependency_released</option>
                          <option value="dependency_blocked">dependency_blocked</option>
                          <option value="stale_worker_update_rejected">stale_worker_update_rejected</option>
                        </select>
                      </div>
                    </div>

                    {/* Timeline List */}
                    <div style={{ maxHeight: '350px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '10px', paddingRight: '4px' }}>
                      {pipelineTimeline.length === 0 ? (
                        <div style={{ padding: '30px 0', textAlign: 'center', color: '#64748b', fontSize: '0.85rem' }}>
                          No audit events registered for this pipeline.
                        </div>
                      ) : (
                        (() => {
                          const filtered = pipelineTimeline.filter(log => {
                            if (timelineFilter !== 'all' && log.event_type !== timelineFilter) return false;
                            if (timelineSearch) {
                              const q = timelineSearch.toLowerCase();
                              return (
                                log.message?.toLowerCase().includes(q) ||
                                log.worker_id?.toLowerCase().includes(q) ||
                                log.task_type?.toLowerCase().includes(q) ||
                                String(log.task_id).includes(q) ||
                                log.event_type?.toLowerCase().includes(q)
                              );
                            }
                            return true;
                          });

                          if (filtered.length === 0) {
                            return (
                              <div style={{ padding: '30px 0', textAlign: 'center', color: '#64748b', fontSize: '0.85rem' }}>
                                No matching events found for the active filter.
                              </div>
                            );
                          }

                          return filtered.map((log) => {
                            let badgeColor = '#64748b';

                            if (log.event_type === 'task_completed' || log.event_type === 'dependency_released') {
                              badgeColor = '#10b981';
                            } else if (log.event_type === 'task_failed' || log.event_type === 'lease_expired' || log.event_type === 'dependency_blocked' || log.event_type === 'stale_worker_update_rejected') {
                              badgeColor = '#ef4444';
                            } else if (log.event_type === 'task_started' || log.event_type === 'task_claimed') {
                              badgeColor = '#3b82f6';
                            } else if (log.event_type === 'task_recovered') {
                              badgeColor = '#8b5cf6';
                            } else if (log.event_type === 'artifact_created') {
                              badgeColor = '#059669';
                            } else if (log.event_type === 'lease_renewed') {
                              badgeColor = '#fbbf24';
                            }

                            return (
                              <div 
                                key={log.id} 
                                style={{
                                  background: 'var(--bg-panel)',
                                  borderLeft: `4px solid ${badgeColor}`,
                                  border: '1px solid var(--border-subtle)',
                                  borderRadius: '6px',
                                  padding: '10px 14px',
                                  display: 'flex',
                                  flexDirection: 'column',
                                  gap: '4px'
                                }}
                              >
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                    <span style={{
                                      fontSize: '0.65rem',
                                      fontWeight: '800',
                                      textTransform: 'uppercase',
                                      color: '#ffffff',
                                      background: badgeColor,
                                      padding: '1px 6px',
                                      borderRadius: '4px'
                                    }}>
                                      {log.event_type}
                                    </span>
                                    <span style={{ fontSize: '0.75rem', fontWeight: 'bold', color: '#cbd5e1' }}>
                                      {log.task_type.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')} (Task #{log.task_id})
                                    </span>
                                  </div>
                                  <span style={{ fontSize: '0.65rem', color: '#64748b' }}>
                                    {new Date(log.created_at).toLocaleTimeString()}
                                  </span>
                                </div>

                                <div style={{ fontSize: '0.8rem', color: '#cbd5e1', lineHeight: '1.4' }}>
                                  {log.message}
                                </div>

                                <div style={{ display: 'flex', gap: '12px', fontSize: '0.65rem', color: '#64748b', borderTop: '1px solid rgba(148, 163, 184, 0.03)', paddingTop: '4px', marginTop: '2px' }}>
                                  {log.worker_id && (
                                    <span>⚙ <strong>Worker:</strong> {log.worker_id}</span>
                                  )}
                                  <span>ℹ <strong>Pipeline:</strong> #{log.pipeline_id}</span>
                                </div>
                              </div>
                            );
                          });
                        })()
                      )}
                    </div>
                  </div>
                )}

              </div>
            </>
          ) : (
            <div className="empty-state-container" style={{ flex: 1, minHeight: '400px', padding: '60px' }}>
              <GitBranch size={48} className="empty-state-icon" />
              <h3 className="empty-state-title" style={{ fontSize: '1.1rem' }}>No Pipeline Selected</h3>
              <p className="empty-state-text" style={{ maxWidth: '380px' }}>
                Launch a demo pipeline on the left or select an existing instance to visualize its DAG nodes, execution states, and filesystem artifacts.
              </p>
            </div>
          )}

          {/* Semantic Search Panel (Phase 4) */}
          <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '4px', padding: '24px' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: '800', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
              <Database size={20} className="text-purple" style={{ color: '#8b5cf6' }} />
              Semantic Search (Phase 4)
            </h3>

            {/* Qdrant Status Banner */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', background: 'var(--bg-panel)', padding: '12px', borderRadius: '4px', marginBottom: '20px', fontSize: '0.8rem', border: '1px solid var(--border-subtle)' }}>
              <div>
                <span style={{ color: '#64748b', display: 'block' }}>Qdrant Collection</span>
                <span style={{ fontWeight: '600', color: '#e2e8f0' }}>{vectorStats?.collection || 'scaleflow_chunks'}</span>
              </div>
              <div>
                <span style={{ color: '#64748b', display: 'block' }}>Total Vectors</span>
                <span style={{ fontWeight: '600', color: '#10b981', fontSize: '1rem' }}>{vectorStats?.points_count !== undefined ? vectorStats.points_count : '...'}</span>
              </div>
              <div>
                <span style={{ color: '#64748b', display: 'block' }}>Qdrant Status</span>
                <span style={{ 
                  fontWeight: 'bold', 
                  color: vectorStats?.status === 'ok' ? '#10b981' : '#ef4444',
                  textTransform: 'uppercase'
                }}>
                  {vectorStats?.status || 'OFFLINE'}
                </span>
              </div>
            </div>

            {/* Search Form */}
            <form onSubmit={handleSearch}>
              <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '16px' }}>
                <div style={{ flex: 1, minWidth: '200px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <label style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Search Query</label>
                  <input 
                    type="text" 
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Enter search phrase (e.g. task recovery)..."
                    style={{
                      padding: '10px',
                      fontSize: '0.85rem',
                      background: 'rgba(0, 0, 0, 0.2)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: '4px',
                      color: '#f1f5f9'
                    }}
                  />
                </div>

                <div style={{ width: '80px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <label style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Top K</label>
                  <select 
                    value={topK}
                    onChange={(e) => setTopK(parseInt(e.target.value))}
                    style={{
                      padding: '10px',
                      fontSize: '0.85rem',
                      background: 'rgba(0, 0, 0, 0.2)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: '4px',
                      color: '#f1f5f9'
                    }}
                  >
                    <option value="3">3</option>
                    <option value="5">5</option>
                    <option value="10">10</option>
                  </select>
                </div>

                <div style={{ display: 'flex', alignItems: 'flex-end' }}>
                  <button 
                    type="submit"
                    disabled={searching || !searchQuery}
                    style={{
                      background: 'var(--color-accent)',
                      color: '#ffffff',
                      border: 'none',
                      borderRadius: '4px',
                      padding: '10px 20px',
                      fontSize: '0.85rem',
                      fontWeight: '600',
                      cursor: searching || !searchQuery ? 'not-allowed' : 'pointer',
                      opacity: searching || !searchQuery ? 0.6 : 1,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      height: '38px'
                    }}
                  >
                    {searching ? <RefreshCw className="animate-spin" size={14} /> : <Search size={14} />}
                    Search
                  </button>
                </div>
              </div>

              {/* Filter */}
              <div style={{ display: 'flex', gap: '16px', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '16px', borderTop: '1px dashed var(--border-subtle)', paddingTop: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <input 
                    type="checkbox" 
                    id="filter-pipeline-chk"
                    checked={!!searchFilterPipeline} 
                    onChange={(e) => setSearchFilterPipeline(e.target.checked ? (selectedPipelineId || 'all') : '')} 
                  />
                  <label htmlFor="filter-pipeline-chk" style={{ cursor: 'pointer' }}>Filter to current pipeline {selectedPipelineId ? `(#${selectedPipelineId})` : ''}</label>
                </div>
              </div>
            </form>

            {/* Search Results list */}
            <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '16px' }}>
              <h4 style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '12px', fontWeight: '600' }}>Results:</h4>
              
              {searchResults.length === 0 ? (
                <div style={{ padding: '20px 0', textAlign: 'center', color: '#64748b', fontSize: '0.85rem' }}>
                  No search results. Enter a query to find matching document chunks.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '300px', overflowY: 'auto' }}>
                  {searchResults.map((r, idx) => (
                    <div key={idx} style={{ background: 'rgba(0, 0, 0, 0.2)', border: '1px solid var(--border-subtle)', borderRadius: '4px', padding: '12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', fontSize: '0.75rem' }}>
                        <span style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#10b981', padding: '2px 8px', borderRadius: '4px', fontWeight: 'bold' }}>
                          Score: {r.score}
                        </span>
                        <span style={{ color: '#94a3b8' }}>
                          Chunk {r.chunk_index} | File: <span style={{ color: '#cbd5e1' }}>{r.original_filename || `ID ${r.file_id}`}</span> | Pipeline: <span style={{ color: '#a78bfa', cursor: 'pointer', textDecoration: 'underline' }} onClick={() => setSelectedPipelineId(r.pipeline_id)}>#{r.pipeline_id}</span>
                        </span>
                      </div>
                      <div style={{ fontSize: '0.8rem', color: '#cbd5e1', lineHeight: '1.4', fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
                        {r.chunk_text}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Retrieval Pipeline Panel (Phase 5) */}
          <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '4px', padding: '24px', marginTop: '20px' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: '800', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
              <Sparkles size={20} className="text-indigo" style={{ color: '#818cf8' }} />
              Retrieval Pipeline (Phase 5)
            </h3>

            {/* Pipeline Configuration Form */}
            <form onSubmit={handleRunRetrievalPipeline}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '20px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <label style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: '600' }}>Retrieval Query</label>
                  <input 
                    type="text" 
                    value={retrievalQuery}
                    onChange={(e) => setRetrievalQuery(e.target.value)}
                    placeholder="Ask a question (e.g. How does ScaleFlow recover failed workers?)..."
                    style={{
                      padding: '12px',
                      fontSize: '0.85rem',
                      background: 'rgba(0, 0, 0, 0.2)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: '4px',
                      color: '#f1f5f9',
                      width: '100%',
                      boxSizing: 'border-box'
                    }}
                  />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '12px' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <label style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: '600' }}>Top K Chunks</label>
                    <select 
                      value={retrievalTopK}
                      onChange={(e) => setRetrievalTopK(parseInt(e.target.value))}
                      style={{
                        padding: '10px',
                        fontSize: '0.85rem',
                        background: 'rgba(0, 0, 0, 0.2)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: '4px',
                        color: '#f1f5f9',
                        width: '100%'
                      }}
                    >
                      <option value="3">3 Chunks</option>
                      <option value="5">5 Chunks</option>
                      <option value="10">10 Chunks</option>
                    </select>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <label style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: '600' }}>Pipeline ID Filter</label>
                    <select 
                      value={retrievalPipelineFilter}
                      onChange={(e) => setRetrievalPipelineFilter(e.target.value)}
                      style={{
                        padding: '10px',
                        fontSize: '0.85rem',
                        background: 'rgba(0, 0, 0, 0.2)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: '4px',
                        color: '#f1f5f9',
                        width: '100%',
                        outline: 'none'
                      }}
                    >
                      <option value="">All Pipelines (No Filter)</option>
                      {pipelines.map(p => (
                        <option key={p.id} value={p.id}>#{p.id} - {p.name}</option>
                      ))}
                    </select>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <label style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: '600' }}>File ID Filter</label>
                    <select 
                      value={retrievalFileFilter}
                      onChange={(e) => setRetrievalFileFilter(e.target.value)}
                      style={{
                        padding: '10px',
                        fontSize: '0.85rem',
                        background: 'rgba(0, 0, 0, 0.2)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: '4px',
                        color: '#f1f5f9',
                        width: '100%',
                        outline: 'none'
                      }}
                    >
                      <option value="">All Files (No Filter)</option>
                      {uploadedFiles.map(f => (
                        <option key={f.id} value={f.id}>{f.original_filename} (ID: {f.id})</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '4px' }}>
                  <button 
                    type="submit"
                    disabled={retrievalRunning || !retrievalQuery}
                    style={{
                      background: 'linear-gradient(135deg, #818cf8 0%, #6366f1 100%)',
                      color: '#ffffff',
                      border: 'none',
                      borderRadius: '4px',
                      padding: '12px 24px',
                      fontSize: '0.875rem',
                      fontWeight: '600',
                      cursor: retrievalRunning || !retrievalQuery ? 'not-allowed' : 'pointer',
                      opacity: retrievalRunning || !retrievalQuery ? 0.6 : 1,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      transition: 'all 0.2s',
                      boxShadow: 'none'
                    }}
                  >
                    {retrievalRunning ? <RefreshCw className="animate-spin" size={16} /> : <Play size={16} />}
                    Run Retrieval Pipeline
                  </button>
                </div>
              </div>
            </form>

            {/* Pipeline Execution Progress / Output */}
            {createdQueryPipelineId && (
              <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-panel)', padding: '12px 16px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
                  <div>
                    <span style={{ fontSize: '0.75rem', color: '#64748b', display: 'block' }}>Pipeline instance</span>
                    <span style={{ fontSize: '0.9rem', fontWeight: 'bold', color: '#cbd5e1' }}>
                      Retrieval Pipeline <span style={{ color: '#818cf8', cursor: 'pointer', textDecoration: 'underline' }} onClick={() => setSelectedPipelineId(createdQueryPipelineId)}>#{createdQueryPipelineId}</span>
                    </span>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <span style={{ fontSize: '0.75rem', color: '#64748b', display: 'block' }}>Status</span>
                    <span className={`badge ${retrievalPipelineProgress?.pipeline?.status || 'created'}`} style={{ fontSize: '0.75rem', padding: '2px 8px', borderRadius: '4px', textTransform: 'uppercase', fontWeight: 'bold' }}>
                      {retrievalPipelineProgress?.pipeline?.status || 'created'}
                    </span>
                  </div>
                </div>

                {/* Progress bar / Nodes */}
                {retrievalPipelineProgress?.tasks && (
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '8px' }}>
                      <span>Retrieval Task DAG Status</span>
                      <span>
                        {retrievalPipelineProgress.tasks.filter(t => t.status === 'completed').length} / {retrievalPipelineProgress.tasks.length} Completed
                      </span>
                    </div>
                    <div style={{ display: 'flex', gap: '6px', width: '100%' }}>
                      {retrievalPipelineProgress.tasks.map((task, idx) => {
                        let color = 'var(--border-subtle)';
                        if (task.status === 'completed') color = '#10b981';
                        else if (task.status === 'failed') color = '#ef4444';
                        else if (task.status === 'running') color = '#3b82f6';
                        else if (task.status === 'pending') color = '#64748b';
                        
                        return (
                          <div key={task.id} style={{ flex: 1, height: '6px', background: color, borderRadius: '3px', position: 'relative' }} title={`${task.type}: ${task.status}`}>
                            <div style={{ position: 'absolute', top: '10px', left: 0, right: 0, textAlign: 'center', fontSize: '0.6rem', color: '#64748b', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {task.type}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                    <div style={{ height: '20px' }}></div>
                  </div>
                )}

                {/* Final Answer Display */}
                {retrievalAnswer && retrievalAnswer.final_answer ? (
                  <div style={{ background: 'rgba(99, 102, 241, 0.05)', border: '1px solid rgba(99, 102, 241, 0.2)', borderRadius: '4px', padding: '20px', marginTop: '10px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                      <h4 style={{ fontSize: '0.9rem', fontWeight: 'bold', color: '#818cf8', margin: 0, display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Cpu size={16} /> Synthesized Answer
                      </h4>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Confidence:</span>
                        <span style={{
                          fontSize: '0.7rem',
                          fontWeight: 'bold',
                          textTransform: 'uppercase',
                          padding: '2px 8px',
                          borderRadius: '4px',
                          background: retrievalAnswer.final_answer.confidence === 'high' ? 'rgba(16, 185, 129, 0.15)' : retrievalAnswer.final_answer.confidence === 'medium' ? 'rgba(245, 158, 11, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                          color: retrievalAnswer.final_answer.confidence === 'high' ? '#10b981' : retrievalAnswer.final_answer.confidence === 'medium' ? '#f59e0b' : '#ef4444'
                        }}>
                          {retrievalAnswer.final_answer.confidence}
                        </span>
                      </div>
                    </div>

                    <div style={{ fontSize: '0.875rem', color: '#e2e8f0', lineHeight: '1.6', whiteSpace: 'pre-wrap', marginBottom: '20px', background: 'var(--bg-panel)', padding: '16px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
                      {retrievalAnswer.final_answer.answer}
                    </div>

                    {/* Citations list */}
                    {retrievalAnswer.final_answer.citations && retrievalAnswer.final_answer.citations.length > 0 && (
                      <div>
                        <h5 style={{ fontSize: '0.8rem', fontWeight: '700', color: '#94a3b8', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <BookOpen size={14} /> Citations & Source Chunks
                        </h5>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                          {retrievalAnswer.final_answer.citations.map((c, cidx) => (
                            <div key={cidx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-panel)', padding: '8px 12px', borderRadius: '6px', fontSize: '0.75rem', border: '1px solid var(--border-subtle)' }}>
                              <span style={{ color: '#cbd5e1' }}>
                                [{cidx + 1}] File: <strong style={{ color: '#cbd5e1' }}>{c.original_filename}</strong> (Chunk {c.chunk_index})
                              </span>
                              <span style={{ color: '#64748b' }}>
                                File ID: {c.file_id}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  retrievalRunning && (
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '30px', color: '#94a3b8', gap: '10px' }}>
                      <RefreshCw className="animate-spin text-indigo" size={24} style={{ color: '#818cf8' }} />
                      <span style={{ fontSize: '0.85rem' }}>Orchestrating retrieval DAG, retrieving context from Qdrant, and synthesizing final report...</span>
                    </div>
                  )
                )}
              </div>
            )}
          </div>

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
          backdropFilter: 'none',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 1000
        }}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{
            background: '#1e293b',
            border: '1px solid #334155',
            borderRadius: '4px',
            width: '90%',
            maxWidth: '700px',
            maxHeight: '85vh',
            display: 'flex',
            flexDirection: 'column',
            boxShadow: 'none',
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
                    <div style={{ color: '#ef4444', marginTop: '12px', padding: '12px', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '4px', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
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
                  borderRadius: '4px',
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
        </>
      )}

      {dashboardTab === 'observability' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', marginTop: '10px' }}>
          {/* 1. Health Status Banner */}
          {systemMetricsData && (() => {
            const health = systemMetricsData.health_state || 'healthy';
            const reason = systemMetricsData.health_reason || 'System operating normally.';
            const isBpActive = backpressureData?.backpressure_active;
            
            let healthColor = '#10b981';
            let healthBg = 'rgba(16, 185, 129, 0.08)';
            let healthBorder = 'rgba(16, 185, 129, 0.2)';
            
            if (health === 'degraded') {
              healthColor = '#fbbf24';
              healthBg = 'rgba(245, 158, 11, 0.08)';
              healthBorder = 'rgba(245, 158, 11, 0.2)';
            } else if (health === 'saturated') {
              healthColor = '#f97316';
              healthBg = 'rgba(249, 115, 22, 0.08)';
              healthBorder = 'rgba(249, 115, 22, 0.2)';
            } else if (health === 'critical') {
              healthColor = '#ef4444';
              healthBg = 'rgba(239, 68, 68, 0.08)';
              healthBorder = 'rgba(239, 68, 68, 0.2)';
            }

            return (
              <div style={{ 
                display: 'grid', 
                gridTemplateColumns: 'repeat(12, 1fr)', 
                gap: '20px',
                background: healthBg,
                border: `1px solid ${healthBorder}`,
                borderRadius: '4px',
                padding: '20px'
              }}>
                <div style={{ gridColumn: 'span 7', display: 'flex', gap: '16px', alignItems: 'center' }}>
                  <div style={{ 
                    width: '16px', 
                    height: '16px', 
                    borderRadius: '50%', 
                    background: healthColor,
                    boxShadow: `0 0 12px ${healthColor}`
                  }} className={health === 'critical' ? 'animate-pulse' : ''} />
                  <div>
                    <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: '800', color: '#ffffff', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      System Status: <span style={{ color: healthColor }}>{health}</span>
                    </h3>
                    <p style={{ margin: '4px 0 0 0', fontSize: '0.85rem', color: '#94a3b8' }}>
                      {reason}
                    </p>
                  </div>
                </div>

                <div style={{ gridColumn: 'span 5', borderLeft: '1px solid var(--border-subtle)', paddingLeft: '20px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '4px' }}>
                    <span style={{ color: '#94a3b8' }}>Backpressure Protection:</span>
                    <span style={{ fontWeight: 'bold', color: isBpActive ? '#ef4444' : '#10b981' }}>
                      {isBpActive ? 'ACTIVE (THROTTLED)' : 'INACTIVE (NORMAL)'}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                    <span style={{ color: '#94a3b8' }}>Deferred Task Backlog:</span>
                    <span style={{ fontWeight: 'bold', color: backpressureData?.deferred_tasks_count > 0 ? '#fbbf24' : '#f8fafc' }}>
                      {backpressureData?.deferred_tasks_count || 0} paused tasks
                    </span>
                  </div>
                </div>
              </div>
            );
          })()}

          {/* 2. Metrics Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(12, 1fr)', gap: '20px' }}>
            
            {/* Queue Pressures & Forecasts Card */}
            <div style={{ gridColumn: 'span 4', background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '4px', padding: '20px' }}>
              <h3 style={{ fontSize: '1rem', fontWeight: '800', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                <Gauge size={16} className="text-purple" style={{ color: '#a78bfa' }} />
                Queue Saturation & Drain
              </h3>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div style={{ background: 'var(--bg-panel)', padding: '12px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
                  <span style={{ fontSize: '0.75rem', color: '#64748b', display: 'block' }}>Total Queue Backlog</span>
                  <span style={{ fontSize: '1.8rem', fontWeight: '800', color: '#ffffff' }}>
                    {systemMetricsData?.metrics?.backlog_size || 0}
                  </span>
                  <span style={{ fontSize: '0.7rem', color: '#94a3b8', display: 'block', marginTop: '4px' }}>
                    High: {systemMetricsData?.metrics?.queue_sizes?.high || 0} | Med: {systemMetricsData?.metrics?.queue_sizes?.medium || 0} | Low: {systemMetricsData?.metrics?.queue_sizes?.low || 0}
                  </span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '8px', fontSize: '0.8rem' }}>
                  <span style={{ color: '#94a3b8' }}>Est. Saturation Time:</span>
                  <span style={{ fontWeight: 'bold', color: scalingData?.estimated_saturation_time_seconds ? '#ef4444' : '#10b981' }}>
                    {scalingData && scalingData.estimated_saturation_time_seconds !== null && scalingData.estimated_saturation_time_seconds !== undefined ? `${scalingData.estimated_saturation_time_seconds}s` : 'Stable / Normal'}
                  </span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '8px', fontSize: '0.8rem' }}>
                  <span style={{ color: '#94a3b8' }}>Est. Recovery Time (to safe limit):</span>
                  <span style={{ fontWeight: 'bold', color: '#fbbf24' }}>
                    {scalingData && scalingData.projected_recovery_time_seconds !== null && scalingData.projected_recovery_time_seconds !== undefined && scalingData.projected_recovery_time_seconds !== 9999 && scalingData.projected_recovery_time_seconds > 0 
                      ? `${scalingData.projected_recovery_time_seconds}s` 
                      : scalingData?.projected_recovery_time_seconds === 9999 || scalingData?.projected_recovery_time_seconds === 'Infinite (Saturated)'
                        ? 'Infinite (Saturated)' 
                        : 'Immediate / Safe'}
                  </span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                  <span style={{ color: '#94a3b8' }}>Est. Drain Completion:</span>
                  <span style={{ fontWeight: 'bold', color: '#cbd5e1' }}>
                    {scalingData?.current_estimated_drain_time_seconds === 'Infinite (Saturated)'
                      ? 'Infinite (Saturated)'
                      : scalingData && scalingData.current_estimated_drain_time_seconds > 0
                        ? `${scalingData.current_estimated_drain_time_seconds}s`
                        : 'No Backlog'}
                  </span>
                </div>
              </div>
            </div>

            {/* Smoothed Rates Card */}
            <div style={{ gridColumn: 'span 4', background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '4px', padding: '20px' }}>
              <h3 style={{ fontSize: '1rem', fontWeight: '800', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                <Activity size={16} className="text-blue" style={{ color: '#60a5fa' }} />
                Smoothed Throughput Rates
              </h3>

              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.75rem', color: '#cbd5e1' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: '#94a3b8', textAlign: 'left' }}>
                    <th style={{ padding: '6px 0' }}>Window</th>
                    <th style={{ padding: '6px 0' }}>Enqueue Rate</th>
                    <th style={{ padding: '6px 0' }}>Dequeue Rate</th>
                    <th style={{ padding: '6px 0' }}>Completions</th>
                  </tr>
                </thead>
                <tbody>
                  <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                    <td style={{ padding: '8px 0', fontWeight: 'bold' }}>10s rolling</td>
                    <td style={{ padding: '8px 0' }}>{systemMetricsData?.metrics?.enqueue_rate?.['10s'] || 0}/s</td>
                    <td style={{ padding: '8px 0' }}>{systemMetricsData?.metrics?.dequeue_rate?.['10s'] || 0}/s</td>
                    <td style={{ padding: '8px 0' }}>{systemMetricsData?.metrics?.completed_count?.['10s'] || 0}</td>
                  </tr>
                  <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                    <td style={{ padding: '8px 0', fontWeight: 'bold' }}>30s rolling</td>
                    <td style={{ padding: '8px 0' }}>{systemMetricsData?.metrics?.enqueue_rate?.['30s'] || 0}/s</td>
                    <td style={{ padding: '8px 0' }}>{systemMetricsData?.metrics?.dequeue_rate?.['30s'] || 0}/s</td>
                    <td style={{ padding: '8px 0' }}>{systemMetricsData?.metrics?.completed_count?.['30s'] || 0}</td>
                  </tr>
                  <tr>
                    <td style={{ padding: '8px 0', fontWeight: 'bold' }}>60s rolling</td>
                    <td style={{ padding: '8px 0' }}>{systemMetricsData?.metrics?.enqueue_rate?.['60s'] || 0}/s</td>
                    <td style={{ padding: '8px 0' }}>{systemMetricsData?.metrics?.dequeue_rate?.['60s'] || 0}/s</td>
                    <td style={{ padding: '8px 0' }}>{systemMetricsData?.metrics?.completed_count?.['60s'] || 0}</td>
                  </tr>
                </tbody>
              </table>

              <div style={{ borderTop: '1px dashed var(--border-subtle)', marginTop: '12px', paddingTop: '10px', display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                <div>
                  <span style={{ color: '#64748b', display: 'block' }}>Avg. Wait Duration</span>
                  <span style={{ fontWeight: 'bold', color: '#ffffff' }}>{systemMetricsData?.metrics?.average_queue_wait_time_seconds || 0}s</span>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span style={{ color: '#64748b', display: 'block' }}>Avg. Exec Duration</span>
                  <span style={{ fontWeight: 'bold', color: '#ffffff' }}>{systemMetricsData?.metrics?.average_task_execution_time_seconds || 0}s</span>
                </div>
              </div>
            </div>

            {/* Autoscaling Simulation Panel */}
            <div style={{ gridColumn: 'span 4', background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '4px', padding: '20px' }}>
              <h3 style={{ fontSize: '1rem', fontWeight: '800', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                <Zap size={16} className="text-pink" style={{ color: '#f472b6' }} />
                Autoscaling Intelligence
              </h3>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                  <div style={{ background: 'var(--bg-panel)', padding: '10px', borderRadius: '4px', textAlign: 'center' }}>
                    <span style={{ fontSize: '0.65rem', color: '#64748b', display: 'block' }}>Current Workers</span>
                    <span style={{ fontSize: '1.4rem', fontWeight: '800', color: '#ffffff' }}>
                      {scalingData?.current_workers || 0}
                    </span>
                  </div>
                  <div style={{ background: 'var(--bg-panel)', padding: '10px', borderRadius: '4px', textAlign: 'center', border: '1px solid rgba(139, 92, 246, 0.15)' }}>
                    <span style={{ fontSize: '0.65rem', color: '#64748b', display: 'block' }}>Recommended</span>
                    <span style={{ fontSize: '1.4rem', fontWeight: '800', color: '#a78bfa' }}>
                      {scalingData?.recommended_workers || 0}
                    </span>
                  </div>
                </div>

                <div style={{ background: 'rgba(139, 92, 246, 0.05)', padding: '12px', borderRadius: '4px', border: '1px dashed rgba(139, 92, 246, 0.2)', textAlign: 'center' }}>
                  <span style={{ fontSize: '0.75rem', color: '#94a3b8', display: 'block' }}>Autoscaling Simulation Action:</span>
                  <span style={{ fontSize: '0.95rem', fontWeight: '800', color: '#ffffff', display: 'block', marginTop: '4px' }}>
                    {scalingData?.scale_up_recommendation > 0 && `Scale UP by +${scalingData.scale_up_recommendation} workers`}
                    {scalingData?.scale_down_recommendation > 0 && `Scale DOWN by -${scalingData.scale_down_recommendation} workers`}
                    {scalingData?.scale_up_recommendation === 0 && scalingData?.scale_down_recommendation === 0 && 'NO ACTION REQUIRED (STABLE)'}
                  </span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                  <span style={{ color: '#64748b' }}>Post-Scaling Drain Time:</span>
                  <span style={{ fontWeight: 'bold', color: '#a78bfa' }}>
                    {scalingData?.projected_drain_time_after_scaling_seconds > 0 
                      ? `${scalingData.projected_drain_time_after_scaling_seconds}s` 
                      : 'No Backlog'}
                  </span>
                </div>
              </div>
            </div>

          </div>

          {/* 3. Workers Pool Table & Reliability Scores */}
          <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '4px', padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '1.1rem', fontWeight: '800', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '8px', margin: 0 }}>
                <Server size={18} className="text-emerald" style={{ color: '#34d399' }} />
                Active Worker Reliability & Recovery Analytics
              </h3>
              
              {systemMetricsData && (
                <div style={{ display: 'flex', gap: '16px', fontSize: '0.85rem' }}>
                  <span>Worker Pool Utilization: <strong style={{ color: '#10b981' }}>{systemMetricsData.metrics?.worker_utilization_percentage || 0}%</strong></span>
                </div>
              )}
            </div>

            {/* Storm Warning */}
            {systemMetricsData?.metrics?.recovery_storm_active && (
              <div className="animate-pulse" style={{ background: 'rgba(239, 68, 68, 0.15)', border: '1px solid #ef4444', color: '#fca5a5', padding: '12px 16px', borderRadius: '4px', marginBottom: '16px', fontSize: '0.85rem', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <AlertTriangle size={18} style={{ color: '#ef4444' }} />
                CRITICAL WARNING: ACTIVE RECOVERY STORM DETECTED (Multiple worker recovery cycles triggered recently).
              </div>
            )}

            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', color: '#cbd5e1' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: '#94a3b8', textAlign: 'left' }}>
                  <th style={{ padding: '10px' }}>Worker ID</th>
                  <th style={{ padding: '10px' }}>Completions (24h)</th>
                  <th style={{ padding: '10px' }}>Failures (24h)</th>
                  <th style={{ padding: '10px' }}>Stales (24h)</th>
                  <th style={{ padding: '10px' }}>Lease Expirations (24h)</th>
                  <th style={{ padding: '10px', width: '200px' }}>Reliability Score</th>
                </tr>
              </thead>
              <tbody>
                {!systemMetricsData?.metrics?.worker_reliability || Object.keys(systemMetricsData.metrics.worker_reliability).length === 0 ? (
                  <tr>
                    <td colSpan="6" style={{ padding: '24px', textAlign: 'center', color: '#64748b' }}>
                      No worker statistics recorded yet. Start workers to populate reliability scores.
                    </td>
                  </tr>
                ) : (
                  Object.entries(systemMetricsData.metrics.worker_reliability).map(([wid, stats]) => {
                    const score = stats.reliability_score || 0;
                    let barColor = '#10b981';
                    if (score < 60) barColor = '#ef4444';
                    else if (score < 85) barColor = '#fbbf24';
                    
                    return (
                      <tr key={wid} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                        <td style={{ padding: '12px 10px', fontWeight: 'bold', color: '#ffffff' }}>{wid}</td>
                        <td style={{ padding: '12px 10px' }}>{stats.completions}</td>
                        <td style={{ padding: '12px 10px', color: stats.failures > 0 ? '#fca5a5' : '#cbd5e1' }}>{stats.failures}</td>
                        <td style={{ padding: '12px 10px', color: stats.stale_incidents > 0 ? '#fca5a5' : '#cbd5e1' }}>{stats.stale_incidents}</td>
                        <td style={{ padding: '12px 10px', color: stats.lease_expirations > 0 ? '#fca5a5' : '#cbd5e1' }}>{stats.lease_expirations}</td>
                        <td style={{ padding: '12px 10px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <span style={{ fontWeight: 'bold', color: barColor, width: '36px' }}>{score}%</span>
                            <div style={{ flex: 1, height: '6px', background: '#334155', borderRadius: '4px', overflow: 'hidden' }}>
                              <div style={{ width: `${score}%`, height: '100%', background: barColor }} />
                            </div>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          {/* Orchestration Ownership Graph */}
          <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '4px', padding: '24px' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: '800', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px' }}>
              <Cpu size={18} className="text-purple" style={{ color: '#a78bfa' }} />
              Distributed Orchestrator HA Ownership Graph
            </h3>
            
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(12, 1fr)', gap: '20px' }}>
              {/* List of Orchestrator Instances */}
              <div style={{ gridColumn: 'span 6', background: 'var(--bg-panel)', borderRadius: '4px', padding: '16px', border: '1px solid var(--border-subtle)' }}>
                <h4 style={{ margin: '0 0 14px 0', fontSize: '0.85rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Active Coordinators Heartbeats</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {!clusterStatus?.orchestrators || clusterStatus.orchestrators.length === 0 ? (
                    <div style={{ color: '#64748b', fontSize: '0.8rem', padding: '12px', textAlign: 'center' }}>
                      No active orchestrator heartbeats detected.
                    </div>
                  ) : (
                    clusterStatus.orchestrators.map((inst) => {
                      const isLeader = inst.instance_id === clusterStatus?.leader_instance_id;
                      return (
                        <div key={inst.instance_id} style={{
                          background: isLeader ? 'rgba(139, 92, 246, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                          border: isLeader ? '1px solid rgba(139, 92, 246, 0.3)' : '1px solid var(--border-subtle)',
                          borderRadius: '4px',
                          padding: '12px 16px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between'
                        }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                            <div style={{
                              width: '10px',
                              height: '10px',
                              borderRadius: '50%',
                              background: inst.status === 'active' ? '#10b981' : '#ef4444',
                              boxShadow: inst.status === 'active' ? '0 0 8px #10b981' : 'none'
                            }} />
                            <div>
                              <span style={{ fontWeight: 'bold', color: '#ffffff', fontSize: '0.9rem' }}>{inst.instance_id}</span>
                              <span style={{ display: 'block', fontSize: '0.7rem', color: '#64748b', marginTop: '2px' }}>
                                Heartbeat: {inst.last_heartbeat ? new Date(inst.last_heartbeat).toLocaleTimeString() : 'N/A'}
                              </span>
                            </div>
                          </div>
                          {isLeader && (
                            <span style={{
                              background: 'linear-gradient(135deg, #8b5cf6 0%, #d946ef 100%)',
                              color: '#ffffff',
                              fontSize: '0.65rem',
                              fontWeight: 'bold',
                              padding: '2px 8px',
                              borderRadius: '4px',
                              textTransform: 'uppercase',
                              letterSpacing: '0.5px',
                              boxShadow: 'none'
                            }}>
                              Active Leader
                            </span>
                          )}
                        </div>
                      );
                    })
                  )}
                </div>
              </div>

              {/* Leased Pipelines & Ownership Links */}
              <div style={{ gridColumn: 'span 6', background: 'var(--bg-panel)', borderRadius: '4px', padding: '16px', border: '1px solid var(--border-subtle)' }}>
                <h4 style={{ margin: '0 0 14px 0', fontSize: '0.85rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Pipeline Lease Assignments</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {!clusterStatus?.pipeline_leases || clusterStatus.pipeline_leases.length === 0 ? (
                    <div style={{ color: '#64748b', fontSize: '0.8rem', padding: '12px', textAlign: 'center' }}>
                      No active pipelines are leased at the moment.
                    </div>
                  ) : (
                    clusterStatus.pipeline_leases.map((lease) => (
                      <div key={lease.pipeline_id} style={{
                        background: 'rgba(255, 255, 255, 0.02)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: '4px',
                        padding: '12px 16px'
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                          <span style={{ fontWeight: 'bold', color: '#ffffff', fontSize: '0.85rem' }}>
                            Pipeline #{lease.pipeline_id}: {lease.name}
                          </span>
                          <span className={`badge ${lease.status}`} style={{ fontSize: '0.65rem', padding: '2px 6px', borderRadius: '4px' }}>
                            {lease.status}
                          </span>
                        </div>
                        <div style={{ fontSize: '0.75rem', color: '#94a3b8', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                          <div>Owner: <span style={{ color: '#a78bfa', fontWeight: 'bold' }}>{lease.owner_instance_id || 'unassigned'}</span></div>
                          <div>Fencing Token (version): <span style={{ color: '#60a5fa' }}>{lease.ownership_version}</span></div>
                          {lease.owner_lease_expires_at && (
                            <div>Lease Expires: <span style={{ color: '#cbd5e1' }}>{new Date(lease.owner_lease_expires_at).toLocaleTimeString()}</span></div>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Worker Capability Heatmap */}
          <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '4px', padding: '24px' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: '800', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px' }}>
              <Activity size={18} className="text-emerald" style={{ color: '#34d399' }} />
              Worker Capability Registry & Load Heatmap
            </h3>
            
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '16px' }}>
              {workersRegistry.length === 0 ? (
                <div style={{ color: '#64748b', fontSize: '0.8rem', padding: '16px', gridColumn: '1 / -1', textAlign: 'center' }}>
                  No registered workers found in cluster registry.
                </div>
              ) : (
                workersRegistry.map((w) => {
                  const lastSeenDate = new Date(w.last_seen);
                  const isAlive = (new Date() - lastSeenDate) < 15000 && w.status === 'active'; // 15s timeout
                  
                  return (
                    <div key={w.worker_id} style={{
                      background: 'var(--bg-panel)',
                      border: isAlive ? '1px solid rgba(52, 211, 153, 0.25)' : '1px solid var(--border-subtle)',
                      borderRadius: '4px',
                      padding: '16px',
                      position: 'relative'
                    }}>
                      {/* Header */}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                        <span style={{ fontWeight: 'bold', color: '#ffffff', fontSize: '0.9rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '180px' }}>
                          {w.worker_id}
                        </span>
                        <span style={{
                          background: isAlive ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                          color: isAlive ? '#34d399' : '#f87171',
                          fontSize: '0.65rem',
                          fontWeight: 'bold',
                          padding: '2px 6px',
                          borderRadius: '4px'
                        }}>
                          {isAlive ? 'ONLINE' : 'DEAD'}
                        </span>
                      </div>
                      
                      {/* Capabilities */}
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '12px' }}>
                        {w.capabilities?.map((cap) => {
                          let capColor = '#94a3b8';
                          let capBg = 'var(--border-subtle)';
                          if (cap === 'embedding_gpu') {
                            capColor = '#60a5fa'; // Blue
                            capBg = 'rgba(96, 165, 250, 0.15)';
                          } else if (cap === 'summarization_llm') {
                            capColor = '#c084fc'; // Purple
                            capBg = 'rgba(192, 132, 252, 0.15)';
                          } else if (cap === 'cpu_heavy') {
                            capColor = '#34d399'; // Green
                            capBg = 'rgba(52, 211, 153, 0.15)';
                          } else if (cap === 'retrieval_optimized') {
                            capColor = '#fb923c'; // Orange
                            capBg = 'rgba(251, 146, 60, 0.15)';
                          }
                          return (
                            <span key={cap} style={{
                              color: capColor,
                              background: capBg,
                              fontSize: '0.65rem',
                              fontWeight: '600',
                              padding: '2px 6px',
                              borderRadius: '4px'
                            }}>
                              {cap}
                            </span>
                          );
                        })}
                      </div>
                      
                      {/* Details */}
                      <div style={{ fontSize: '0.75rem', color: '#94a3b8', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                        <div>Last Seen: {lastSeenDate.toLocaleTimeString()}</div>
                        {w.resource_limits && Object.keys(w.resource_limits).length > 0 && (
                          <div style={{ display: 'flex', gap: '10px', marginTop: '4px', borderTop: '1px solid var(--border-subtle)', paddingTop: '4px' }}>
                            <span>CPU: {w.resource_limits.cpu_cores || 'N/A'} cores</span>
                            <span>GPU: {w.resource_limits.gpu_memory || 'N/A'}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Failover & Takeover Timeline */}
          <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '4px', padding: '24px' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: '800', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px' }}>
              <Clock size={18} className="text-pink" style={{ color: '#f472b6' }} />
              Cluster Failover & Takeover History
            </h3>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '300px', overflowY: 'auto' }}>
              {clusterFailovers.length === 0 ? (
                <div style={{ color: '#64748b', fontSize: '0.8rem', padding: '16px', textAlign: 'center' }}>
                  No cluster failovers or ownership takeover incidents recorded yet. System is stable.
                </div>
              ) : (
                clusterFailovers.map((fail, idx) => (
                  <div key={fail.id || idx} style={{
                    background: 'rgba(239, 68, 68, 0.05)',
                    borderLeft: '4px solid #ef4444',
                    borderRadius: '0 8px 8px 0',
                    padding: '12px 16px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between'
                  }}>
                    <div>
                      <div style={{ fontWeight: 'bold', color: '#ffffff', fontSize: '0.85rem' }}>
                        Pipeline #{fail.pipeline_id} Taken Over
                      </div>
                      <p style={{ margin: '4px 0 0 0', fontSize: '0.8rem', color: '#cbd5e1' }}>
                        {fail.message} (Version Token: {fail.ownership_version})
                      </p>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#94a3b8', textAlign: 'right' }}>
                      <div>{new Date(fail.timestamp).toLocaleDateString()}</div>
                      <div>{new Date(fail.timestamp).toLocaleTimeString()}</div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* 4. Active Backpressure Config Details */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '20px', background: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--border-subtle)', borderRadius: '4px', padding: '20px', fontSize: '0.8rem', color: '#94a3b8' }}>
            <div>
              <span style={{ fontWeight: 'bold', color: '#e2e8f0', display: 'block', marginBottom: '8px' }}>Active Backpressure Policies</span>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <div>• Overload Protection Policy: <strong>{backpressureData?.config?.overload_protection_policy || 'defer'}</strong> (deferred root tasks)</div>
                <div>• Queue Backlog limit: <strong>{backpressureData?.config?.max_backlog_size || 50} tasks</strong></div>
                <div>• Low Priority Throttle threshold: <strong>{backpressureData?.config?.low_priority_throttle_limit || 5} active tasks</strong></div>
              </div>
            </div>
            <div>
              <span style={{ fontWeight: 'bold', color: '#e2e8f0', display: 'block', marginBottom: '8px' }}>Starvation Prevention & Aging</span>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <div>• Priority Aging Threshold: <strong>{backpressureData?.config?.aging_threshold_seconds || 60} seconds</strong> (wait limit)</div>
                <div>• Queue Scheduler Algorithm: <strong>Weighted Round-Robin (WRR)</strong></div>
                <div>• WRR Target Cycle: <strong>[6 High : 3 Medium : 1 Low]</strong></div>
              </div>
            </div>
          </div>

        </div>
      )}

      {dashboardTab === 'replay' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(12, 1fr)', gap: '24px', marginTop: '10px' }}>
          
          {/* Left Column: Pipeline list & Snapshots */}
          <div style={{ gridColumn: 'span 4', display: 'flex', flexDirection: 'column', gap: '20px' }}>
            
            {/* Pipeline Selector Card */}
            <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '4px', padding: '20px' }}>
              <h3 style={{ fontSize: '1.0rem', fontWeight: '700', marginBottom: '14px', color: '#f1f5f9', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <GitBranch size={16} style={{ color: '#8b5cf6' }} />
                Select Pipeline for Replay
              </h3>
              <select 
                value={replayPipelineId || ''} 
                onChange={(e) => {
                  const val = e.target.value ? parseInt(e.target.value) : null;
                  setReplayPipelineId(val);
                  if (val) loadPipelineReplayData(val);
                }}
                style={{ width: '100%', fontSize: '0.9rem', padding: '10px', background: 'rgba(0, 0, 0, 0.2)', color: '#fff', border: '1px solid var(--border-subtle)', borderRadius: '6px' }}
              >
                <option value="">-- Choose Pipeline --</option>
                {pipelines.map(p => (
                  <option key={p.id} value={p.id}>#{p.id} {p.name} ({p.status})</option>
                ))}
              </select>
            </div>

            {/* Snapshot Watermarks Card */}
            <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '4px', padding: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                <h3 style={{ fontSize: '1.0rem', fontWeight: '700', color: '#f1f5f9', display: 'flex', alignItems: 'center', gap: '8px', margin: 0 }}>
                  <Database size={16} style={{ color: '#a78bfa' }} />
                  Snapshots & Watermarks
                </h3>
                {replayPipelineId && (
                  <button 
                    onClick={async () => {
                      try {
                        await triggerPipelineSnapshot(replayPipelineId);
                        const snaps = await fetchPipelineSnapshots(replayPipelineId);
                        setReplaySnapshots(snaps);
                        alert("Snapshot created successfully!");
                      } catch (err) {
                        alert("Failed to create snapshot: " + err.message);
                      }
                    }}
                    style={{ background: 'rgba(139, 92, 246, 0.2)', border: '1px solid rgba(139, 92, 246, 0.4)', borderRadius: '4px', padding: '2px 8px', fontSize: '0.7rem', color: '#a78bfa', cursor: 'pointer' }}
                  >
                    Snapshot Now
                  </button>
                )}
              </div>

              {replaySnapshots.length === 0 ? (
                <div style={{ fontSize: '0.8rem', color: '#64748b', textAlign: 'center', padding: '20px 0' }}>
                  No snapshots created yet. Periodic snapshots are auto-created every 10 events.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '180px', overflowY: 'auto' }}>
                  {replaySnapshots.map(snap => (
                    <div 
                      key={snap.id}
                      style={{ 
                        display: 'flex', 
                        justifyContent: 'space-between', 
                        alignItems: 'center', 
                        background: 'var(--bg-panel)', 
                        padding: '8px 12px', 
                        borderRadius: '6px', 
                        border: '1px solid var(--border-subtle)',
                        fontSize: '0.75rem'
                      }}
                    >
                      <div>
                        <div style={{ fontWeight: 'bold', color: '#e2e8f0' }}>Snapshot #{snap.id}</div>
                        <span style={{ color: '#64748b', fontSize: '0.65rem' }}>Watermark Event ID: {snap.last_event_id}</span>
                      </div>
                      <button 
                        onClick={() => {
                          const idx = replayEvents.findIndex(e => e.id === snap.last_event_id);
                          if (idx !== -1) {
                            setReplayScrubberVal(idx + 1);
                          } else {
                            alert("Watermark event not found in memory stream.");
                          }
                        }}
                        style={{ background: '#3b82f6', border: 'none', borderRadius: '4px', padding: '2px 8px', color: '#fff', cursor: 'pointer', fontSize: '0.7rem' }}
                      >
                        Restore
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Global Live Event Stream Banner */}
            <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '4px', padding: '20px', flex: 1, display: 'flex', flexDirection: 'column' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                <h3 style={{ fontSize: '1.0rem', fontWeight: '700', color: '#f1f5f9', display: 'flex', alignItems: 'center', gap: '8px', margin: 0 }}>
                  <Activity size={16} style={{ color: '#10b981' }} />
                  Global Event Stream
                </h3>
                <select 
                  value={globalEventCategory} 
                  onChange={(e) => setGlobalEventCategory(e.target.value)}
                  style={{ background: 'rgba(0, 0, 0, 0.25)', border: '1px solid var(--border-subtle)', borderRadius: '4px', padding: '2px', color: '#fff', fontSize: '0.7rem' }}
                >
                  <option value="">All Categories</option>
                  <option value="critical">Critical</option>
                  <option value="operational">Operational</option>
                  <option value="telemetry">Telemetry</option>
                  <option value="debug">Debug</option>
                </select>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', overflowY: 'auto', flex: 1, maxHeight: '350px' }}>
                {globalEvents.map(evt => {
                  let badgeBg = 'var(--border-subtle)';
                  let badgeColor = '#94a3b8';
                  if (evt.event_category === 'critical') { badgeBg = 'rgba(239, 68, 68, 0.1)'; badgeColor = '#fca5a5'; }
                  else if (evt.event_category === 'operational') { badgeBg = 'rgba(59, 130, 246, 0.1)'; badgeColor = '#93c5fd'; }
                  else if (evt.event_category === 'telemetry') { badgeBg = 'rgba(16, 185, 129, 0.1)'; badgeColor = '#86efac'; }
                  
                  return (
                    <div 
                      key={evt.id} 
                      style={{ 
                        fontSize: '0.75rem', 
                        background: 'var(--bg-panel)', 
                        border: '1px solid var(--border-subtle)', 
                        borderRadius: '6px', 
                        padding: '8px'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                        <span style={{ fontWeight: 'bold', color: '#f1f5f9' }}>{evt.event_type}</span>
                        <span style={{ background: badgeBg, color: badgeColor, padding: '1px 6px', borderRadius: '4px', fontSize: '0.65rem', textTransform: 'uppercase' }}>{evt.event_category}</span>
                      </div>
                      <div style={{ color: '#cbd5e1', fontSize: '0.7rem' }}>{evt.message || `Orchestration details for event ID ${evt.id}`}</div>
                      <div style={{ color: '#64748b', fontSize: '0.65rem', display: 'flex', gap: '10px', marginTop: '4px' }}>
                        <span>ID: #{evt.id}</span>
                        {evt.pipeline_id && <span>Pipeline: #{evt.pipeline_id}</span>}
                        {evt.worker_id && <span>Worker: {evt.worker_id}</span>}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

          </div>

          {/* Right Column: Time-Travel Control & Replay Screen */}
          <div style={{ gridColumn: 'span 8', display: 'flex', flexDirection: 'column', gap: '20px' }}>
            
            {replayPipelineId && originalReplayDag ? (
              <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '4px', padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
                
                {/* Header info */}
                <div>
                  <h3 style={{ fontSize: '1.2rem', fontWeight: '800', color: '#fff', margin: 0 }}>
                    Workflow Replay Sandbox
                  </h3>
                  <p style={{ margin: '4px 0 0 0', fontSize: '0.85rem', color: '#94a3b8' }}>
                    Inspect reconstructed workflow states at exact logical event boundaries. Replay operates in a strict sandbox.
                  </p>
                </div>

                {/* Timeline Scrubber Slider */}
                <div style={{ background: 'rgba(0, 0, 0, 0.2)', padding: '16px 20px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '8px' }}>
                    <span>Replay scrubber step: <strong>{replayScrubberVal} / {replayEvents.length}</strong></span>
                    <span style={{ color: '#a78bfa', fontWeight: 'bold' }}>
                      {replayScrubberVal > 0 ? replayEvents[replayScrubberVal - 1]?.event_type : 'START OF PIPELINE'}
                    </span>
                  </div>
                  
                  <input 
                    type="range" 
                    min="0" 
                    max={replayEvents.length} 
                    value={replayScrubberVal} 
                    onChange={(e) => {
                      setReplayStatus('paused');
                      setReplayScrubberVal(parseInt(e.target.value));
                    }}
                    style={{ width: '100%', accentColor: '#8b5cf6', cursor: 'pointer', height: '6px', background: '#334155', borderRadius: '5px' }}
                  />

                  {/* Scrubber ticks description */}
                  {replayScrubberVal > 0 && (
                    <div style={{ marginTop: '8px', fontSize: '0.75rem', background: 'rgba(139, 92, 246, 0.1)', color: '#cbd5e1', padding: '8px', borderRadius: '6px', border: '1px solid rgba(139, 92, 246, 0.15)' }}>
                      <strong>Latest Replayed Event (ID: #{replayEvents[replayScrubberVal - 1]?.id}):</strong>{' '}
                      {replayEvents[replayScrubberVal - 1]?.message || 'No description message.'}
                    </div>
                  )}
                </div>

                {/* Replay control buttons */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', background: 'var(--bg-panel)', padding: '12px 20px', borderRadius: '4px' }}>
                  <div style={{ display: 'flex', gap: '10px' }}>
                    <button 
                      onClick={() => {
                        setReplayStatus('paused');
                        setReplayScrubberVal(0);
                      }}
                      style={{ background: '#334155', color: '#fff', border: 'none', borderRadius: '6px', padding: '6px 12px', fontSize: '0.8rem', fontWeight: 'bold', cursor: 'pointer' }}
                    >
                      ⏮ Jump to Start
                    </button>
                    
                    <button 
                      onClick={() => setReplayStatus(prev => prev === 'playing' ? 'paused' : 'playing')}
                      style={{ 
                        background: replayStatus === 'playing' ? '#ef4444' : 'var(--color-accent)', 
                        color: '#fff', 
                        border: 'none', 
                        borderRadius: '6px', 
                        padding: '6px 16px', 
                        fontSize: '0.8rem', 
                        fontWeight: 'bold', 
                        cursor: 'pointer',
                        boxShadow: replayStatus === 'playing' ? 'none' : '0 2px 8px rgba(139, 92, 246, 0.3)'
                      }}
                    >
                      {replayStatus === 'playing' ? '⏸ Pause' : '▶ Play'}
                    </button>
                    
                    <button 
                      onClick={() => {
                        setReplayStatus('paused');
                        setReplayScrubberVal(prev => Math.min(prev + 1, replayEvents.length));
                      }}
                      style={{ background: '#334155', color: '#fff', border: 'none', borderRadius: '6px', padding: '6px 12px', fontSize: '0.8rem', fontWeight: 'bold', cursor: 'pointer' }}
                    >
                      ⏭ Step Forward
                    </button>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Replay Speed:</span>
                    <select 
                      value={replaySpeed} 
                      onChange={(e) => setReplaySpeed(parseFloat(e.target.value))}
                      style={{ background: 'rgba(0, 0, 0, 0.25)', border: '1px solid var(--border-subtle)', borderRadius: '4px', padding: '4px', color: '#fff', fontSize: '0.8rem' }}
                    >
                      <option value="0.5">0.5x</option>
                      <option value="1.0">1.0x (Normal)</option>
                      <option value="2.0">2.0x</option>
                      <option value="5.0">5.0x</option>
                    </select>
                  </div>
                </div>

                {/* React Flow Replay Visual Screen */}
                <div 
                  style={{ 
                    height: '400px',
                    background: '#090d16', 
                    borderRadius: '4px', 
                    border: '1px solid var(--border-subtle)',
                    position: 'relative',
                    overflow: 'hidden',
                    boxShadow: 'none'
                  }}
                >
                  <ReactFlow
                    nodes={replayNodes}
                    edges={replayEdges}
                    nodeTypes={nodeTypes}
                    fitView
                    fitViewOptions={{ padding: 0.15 }}
                    minZoom={0.05}
                    maxZoom={1.5}
                  >
                    <Background color="#334155" gap={16} size={1} />
                    <Controls showInteractive={false} />
                  </ReactFlow>
                </div>

                {/* Chrono Event Stream for the selected pipeline */}
                <div style={{ marginTop: '10px' }}>
                  <h4 style={{ fontSize: '0.85rem', textTransform: 'uppercase', color: '#94a3b8', letterSpacing: '0.5px', marginBottom: '10px', fontWeight: '700' }}>
                    Replay Event Log (Click to jump to event step)
                  </h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '180px', overflowY: 'auto' }}>
                    {replayEvents.map((evt, idx) => {
                      const isActive = idx < replayScrubberVal;
                      const isCurrent = idx === replayScrubberVal - 1;
                      
                      return (
                        <div 
                          key={evt.id}
                          onClick={() => {
                            setReplayStatus('paused');
                            setReplayScrubberVal(idx + 1);
                          }}
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            padding: '6px 12px',
                            background: isCurrent ? 'rgba(139, 92, 246, 0.2)' : (isActive ? 'var(--bg-panel)' : 'rgba(255, 255, 255, 0.02)'),
                            border: isCurrent ? '1px solid rgba(139, 92, 246, 0.4)' : (isActive ? '1px solid var(--border-subtle)' : '1px solid transparent'),
                            borderRadius: '6px',
                            cursor: 'pointer',
                            fontSize: '0.75rem',
                            opacity: isActive ? 1 : 0.5,
                            transition: 'all 0.15s ease'
                          }}
                        >
                          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                            <span style={{ color: '#a78bfa', fontWeight: 'bold' }}>Step {idx + 1}</span>
                            <span style={{ fontWeight: 'bold', color: '#f1f5f9' }}>{evt.event_type}</span>
                            <span style={{ color: '#94a3b8', fontSize: '0.7rem' }}>— {evt.message}</span>
                          </div>
                          <span style={{ color: '#64748b', fontSize: '0.65rem' }}>{new Date(evt.created_at).toLocaleTimeString()}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>

              </div>
            ) : (
              <div className="empty-state-container" style={{ flex: 1, minHeight: '400px', padding: '60px' }}>
                <GitBranch size={48} className="empty-state-icon" />
                <h3 className="empty-state-title" style={{ fontSize: '1.1rem' }}>No Pipeline Selected</h3>
                <p className="empty-state-text" style={{ maxWidth: '380px' }}>
                  Select a pipeline instance from the dropdown in the left column to reconstruct and time-travel debug its DAG execution path.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default PipelineDashboard;
