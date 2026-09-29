import React, { useState, useMemo, useEffect } from 'react';
import { 
  CheckCircle2, XCircle, Clock, Server, 
  ChevronDown, ChevronRight, GitBranch, LayoutList,
  FileText, Loader2, ArrowRight, Activity,
  Scan, Database, Layers, Grid, Search, FileSignature, X
} from 'lucide-react';
import ReactFlow, { Background, Controls, MarkerType, Handle, Position, MiniMap } from 'reactflow';
import 'reactflow/dist/style.css';
import dagre from 'dagre';

const STAGE_ORDER = [
  'preprocessing',
  'parsing',
  'persistence',
  'validation',
  'chunking',
  'embedding',
  'indexing',
  'summarization'
];

const STAGE_LABELS = {
  preprocessing: 'Preprocessing',
  parsing: 'Parsing',
  persistence: 'Persistence',
  validation: 'Validation',
  chunking: 'Chunking',
  embedding: 'Embedding',
  indexing: 'Indexing',
  summarization: 'Summarization'
};

const STAGE_ICONS = {
  preprocessing: FileText,
  parsing: Scan,
  persistence: Database,
  validation: CheckCircle2,
  chunking: Layers,
  embedding: Grid,
  indexing: Search,
  summarization: FileSignature
};

const getStatusColor = (status) => {
  if (!status) return '#64748b';
  const s = status.toLowerCase();
  if (s === 'completed') return '#22c55e';
  if (s === 'running') return '#3b82f6';
  if (s === 'failed') return '#ef4444';
  if (s === 'queued' || s === 'pending') return '#64748b';
  return '#64748b';
};

const StatusIcon = ({ status, size = 16, className = '' }) => {
  if (!status) return <Clock size={size} color="#64748b" />;
  const s = status.toLowerCase();
  if (s === 'completed') return <CheckCircle2 size={size} color="#22c55e" />;
  if (s === 'failed') return <XCircle size={size} color="#ef4444" />;
  if (s === 'running') return <Loader2 size={size} color="#3b82f6" className={`animate-spin ${className}`} />;
  return <Clock size={size} color="#64748b" />;
};

const formatDuration = (ms, hasMetrics = true) => {
  if (!hasMetrics || ms === null || ms === undefined || ms === '—') return '—';
  if (ms === 0) return '0ms';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  
  const totalSec = ms / 1000;
  if (totalSec < 60) return `${totalSec.toFixed(2)}s`;

  const days = Math.floor(totalSec / 86400);
  const hrs = Math.floor((totalSec % 86400) / 3600);
  const mins = Math.floor((totalSec % 3600) / 60);
  const secs = Math.floor(totalSec % 60);

  if (days > 0) {
    return `${days}d ${hrs}h ${mins}m ${secs}s`;
  }
  if (hrs > 0) {
    return `${hrs}h ${mins}m ${secs}s`;
  }
  return `${mins}m ${secs}s`;
};

const formatIST = (isoString) => {
  if (!isoString) return '—';
  try {
    return new Date(isoString).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', dateStyle: 'medium', timeStyle: 'medium' });
  } catch (e) { return '—'; }
};

const computeTimings = (t, pipelineStatus = 'running') => {
  if (t.exec_time !== undefined && t.queue_wait_time !== undefined && t.exec_time !== null) {
      return { exec: t.exec_time, wait: t.queue_wait_time };
  }
  const isTerminated = ['failed', 'completed', 'cancelled', 'processed'].includes((pipelineStatus || '').toLowerCase());
  const now = isTerminated && t.updated_at ? new Date(t.updated_at).getTime() : Date.now();
  const created = t.created_at ? new Date(t.created_at).getTime() : now;
  let started = t.started_at ? new Date(t.started_at).getTime() : null;
  if (!started && (t.status === 'running' || t.status === 'completed')) started = created;
  let completed = t.completed_at ? new Date(t.completed_at).getTime() : null;
  if (!completed && (t.status === 'running' || t.status === 'failed')) completed = now;
  
  const wait = started ? Math.max(0, started - created) : (isTerminated ? Math.max(0, now - created) : 0);
  const exec = completed && started ? Math.max(0, completed - started) : (started && isTerminated ? Math.max(0, now - started) : 0);
  return { wait, exec };
};

const getLayoutedElements = (nodes, edges, direction = 'LR') => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  
  const nodeWidth = 240;
  const nodeHeight = 96;

  dagreGraph.setGraph({ rankdir: direction, ranksep: 50, nodesep: 40 });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  return { 
    nodes: nodes.map((node) => {
      const nodeWithPosition = dagreGraph.node(node.id) || { x: nodeWidth / 2, y: nodeHeight / 2 };
      return {
        ...node,
        targetPosition: direction === 'LR' ? 'left' : 'top',
        sourcePosition: direction === 'LR' ? 'right' : 'bottom',
        position: {
          x: nodeWithPosition ? nodeWithPosition.x - nodeWidth / 2 : 0,
          y: nodeWithPosition ? nodeWithPosition.y - nodeHeight / 2 : 0,
        },
      };
    }), 
    edges 
  };
};


const CustomDagNode = ({ data }) => {
  const isCritical = data.is_critical_path;
  const isHovered = data.isHovered;
  const isDimmed = data.isDimmed;
  
  const status = data.status || 'pending';
  const hasRun = status === 'completed' || status === 'running' || status === 'failed';
  
  const metric = data.metric;
  const execTimeMs = metric ? metric.e * 1000 : null;
  const queueTimeMs = metric ? metric.q * 1000 : null;
  const totalLatency = data.totalLatency || 1;
  const depWaitPct = metric ? (metric.dw / totalLatency) * 100 : 0;
  const queuePct = metric ? (metric.q / totalLatency) * 100 : 0;
  const execPct = metric ? (metric.e / totalLatency) * 100 : 0;
  
  let borderColor = '#2a2a35';
  let borderStyle = 'solid';
  let bgColor = '#12121a';
  let labelColor = '#e2e8f0';
  let pulsing = false;
  
  if (status === 'completed') {
    borderColor = '#22c55e'; // solid green
  } else if (status === 'running') {
    borderColor = '#3b82f6';
    pulsing = true;
  } else if (status === 'failed') {
    borderColor = '#ef4444';
  } else if (status === 'cancelled') {
    borderColor = '#475569';
    bgColor = 'repeating-linear-gradient(45deg, #12121a, #12121a 10px, #1a1a24 10px, #1a1a24 20px)';
  } else {
    // pending
    borderStyle = 'dashed';
    borderColor = '#475569';
    labelColor = '#94a3b8';
  }

  const StageIcon = STAGE_ICONS[data.stageAssigned] || Clock;
  const friendlyLabel = STAGE_LABELS[data.stageAssigned] || data.task_type;

  return (
    <div 
      style={{
        background: bgColor,
        border: `1px ${borderStyle} ${borderColor}`,
        borderRadius: '8px',
        padding: '12px',
        width: '240px',
        height: '96px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        color: '#fff',
        position: 'relative',
        overflow: 'hidden',
        opacity: isDimmed ? 0.3 : 1,
        transition: 'all 0.2s',
        boxShadow: pulsing ? '0 0 0 2px rgba(59, 130, 246, 0.4)' : 'none',
        animation: pulsing ? 'borderPulse 2s infinite' : 'none'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ fontSize: '14px', fontWeight: 600, color: labelColor, display: 'flex', alignItems: 'center', gap: '6px' }}>
          <StageIcon size={14} color={getStatusColor(status)} />
          <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '160px' }}>
            {friendlyLabel}
          </span>
        </div>
        <StatusIcon status={status} size={14} />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <div style={{ width: '100%', height: '4px', background: '#1f1f2e', borderRadius: '2px', position: 'relative' }}>
          {metric && hasRun && (
            <>
              {queuePct > 0 && <div style={{ position: 'absolute', left: `${depWaitPct}%`, width: `${queuePct}%`, height: '100%', background: '#64748b', borderRadius: '2px 0 0 2px' }} />}
              {execPct > 0 && <div style={{ position: 'absolute', left: `${depWaitPct + queuePct}%`, width: `${execPct}%`, height: '100%', background: getStatusColor(status), borderRadius: queuePct > 0 ? '0 2px 2px 0' : '2px' }} />}
            </>
          )}
        </div>
        <div style={{ fontSize: '11px', color: '#94a3b8', display: 'flex', justifyContent: 'space-between', fontFamily: 'monospace' }}>
           {(!metric || status === 'pending' || status === 'cancelled') ? (
             <span>Not run</span>
           ) : (
             <span>Exec {formatDuration(execTimeMs, true)} · Queue {formatDuration(queueTimeMs, true)}</span>
           )}
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '11px' }}>
        <div style={{ display: 'flex', gap: '6px' }}>
          {isCritical ? (
            <span style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#ef4444', padding: '2px 6px', borderRadius: '4px', border: '1px solid rgba(239, 68, 68, 0.2)' }}>Critical</span>
          ) : data.is_slowest_compute ? (
            <span style={{ background: 'rgba(245, 158, 11, 0.1)', color: '#f59e0b', padding: '2px 6px', borderRadius: '4px', border: '1px solid rgba(245, 158, 11, 0.2)' }}>Slowest compute</span>
          ) : (data.metrics && data.metrics.queue_wait > 1) ? (
            <span style={{ background: 'rgba(245, 158, 11, 0.1)', color: '#f59e0b', padding: '2px 6px', borderRadius: '4px', border: '1px solid rgba(245, 158, 11, 0.2)' }}>
              Queued {formatDuration(data.metrics.queue_wait * 1000, true)}
            </span>
          ) : null}
        </div>
        <div style={{ color: '#64748b' }}>
          {data.assigned_worker_id || data.worker || 'unassigned'}
        </div>
      </div>
      
      <Handle type="target" position={data.direction === 'LR' ? Position.Left : Position.Top} style={{ opacity: 0 }} />
      <Handle type="source" position={data.direction === 'LR' ? Position.Right : Position.Bottom} style={{ opacity: 0 }} />
    </div>
  );
};
const nodeTypes = { customDagNode: CustomDagNode };

const visualizerStyles = `
  @keyframes borderPulse {
    0% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.4); border-color: #3b82f6; }
    70% { box-shadow: 0 0 0 8px rgba(59, 130, 246, 0); border-color: #60a5fa; }
    100% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0); border-color: #3b82f6; }
  }
  .stage-running {
    animation: borderPulse 2s infinite;
  }
  .detail-panel {
    width: 400px;
    background: #08080c;
    padding: 32px;
    overflow-y: auto;
    border-left: 1px solid #1f1f2e;
    transition: transform 0.3s ease;
  }
  @media (max-width: 1024px) {
    .detail-panel {
      position: absolute;
      right: 0;
      top: 0;
      bottom: 0;
      z-index: 50;
      box-shadow: -4px 0 25px rgba(0,0,0,0.7);
      transform: translateX(100%);
    }
    .detail-panel.open {
      transform: translateX(0);
    }
  }
`;

const PipelineVisualizer = ({ tasks = [], pipelineStatus = 'running', metrics = null, onRetryTask }) => {
  const [viewMode, setViewMode] = useState('timeline');
  const [expandedStages, setExpandedStages] = useState({});
  // Use IDs for selection to avoid stale closure references
  const [selectedItemState, setSelectedItemState] = useState(null);
  const [rfInstance, setRfInstance] = useState(null);
  const [hoveredNodeId, setHoveredNodeId] = useState(null);
  const hasMetrics = !!metrics;

  // 1. Live timer refresh if pipeline is running
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let interval;
    if (pipelineStatus !== 'completed' && pipelineStatus !== 'failed' && tasks.some(t => t.status === 'running')) {
      interval = setInterval(() => setTick(t => t + 1), 1000);
    }
    return () => clearInterval(interval);
  }, [pipelineStatus, tasks]);

  const stagesData = useMemo(() => {
    if (!tasks) return [];
    
    const buckets = {};
    STAGE_ORDER.forEach(s => buckets[s] = { 
      name: s, tasks: [], status: 'pending', 
      totalExec: 0, totalDepWait: 0, totalQWait: 0, totalWait: 0, criticalPath: false 
    });
    
    let totalPipelineExecTime = 1;

    let slowestId = null;
    let maxExec = -1;
    if (metrics) {
      tasks.forEach(t => {
        const exec = metrics?.node_weights?.[String(t.id)]?.execution_duration || 0;
        if (exec > maxExec) { maxExec = exec; slowestId = String(t.id); }
      });
    }

    // Enhance tasks with backend-computed timings and stage assignment
    const enhancedTasks = tasks.map(t => {
      const tid = String(t.id);
      const metric = metrics?.node_weights?.[tid] || { dependency_wait: 0, queue_wait: 0, execution_duration: 0 };
      const wait = metric.queue_wait * 1000;
      const exec = metric.execution_duration * 1000;
      const isCritical = metrics?.critical_path?.map(String).includes(tid);
      const isSlowestCompute = tid === slowestId;
      
      const name = (t.type || t.task_type || '').toLowerCase();
      let stageKey = 'preprocessing';
      if (name.includes('valid')) stageKey = 'validation';
      else if (name.includes('pars') || name.includes('ocr')) stageKey = 'parsing';
      else if (name.includes('persist') || name.includes('store') || name.includes('layout')) stageKey = 'persistence';
      else if (name.includes('chunk')) stageKey = 'chunking';
      else if (name.includes('embed')) stageKey = 'embedding';
      else if (name.includes('index')) stageKey = 'indexing';
      else if (name.includes('summari')) stageKey = 'summarization';
      else if (name.includes('upload')) stageKey = 'preprocessing';

      return { 
        ...t, 
        computedWait: wait, 
        computedExec: exec, 
        stageAssigned: stageKey,
        is_critical_path: isCritical,
        is_slowest_compute: isSlowestCompute,
        metrics: metric,
        is_worker_busy: false
      };
    });

    enhancedTasks.forEach(t => {
      if (t.metrics.queue_wait > 1 && (t.assigned_worker_id || t.worker)) {
        const qStart = t.metrics.dependency_wait;
        const qEnd = qStart + t.metrics.queue_wait;
        const workerId = t.assigned_worker_id || t.worker;
        const overlapping = enhancedTasks.find(t2 => {
          if (t2.id === t.id) return false;
          if ((t2.assigned_worker_id || t2.worker) !== workerId) return false;
          const eStart = t2.metrics.dependency_wait + t2.metrics.queue_wait;
          const eEnd = eStart + t2.metrics.execution_duration;
          return eStart < qEnd && eEnd > qStart;
        });
        if (overlapping) t.is_worker_busy = true;
      }
    });

    enhancedTasks.forEach(t => {
      const stage = buckets[t.stageAssigned];
      stage.tasks.push(t);
      stage.totalExec += t.computedExec;
      stage.totalDepWait += (t.metrics.dependency_wait || 0) * 1000;
      stage.totalQWait += (t.metrics.queue_wait || 0) * 1000;
      stage.totalWait += (t.metrics.queue_wait || 0) * 1000;
      totalPipelineExecTime += t.computedExec;
      if (t.is_critical_path) stage.criticalPath = true;
    });

    Object.values(buckets).forEach(stage => {
      if (stage.tasks.length === 0) {
        stage.status = 'queued';
        return;
      }
      const hasFailed = stage.tasks.some(t => t.status === 'failed');
      const hasRunning = stage.tasks.some(t => t.status === 'running');
      const allCompleted = stage.tasks.every(t => t.status === 'completed');
      
      if (hasFailed) stage.status = 'failed';
      else if (hasRunning) stage.status = 'running';
      else if (allCompleted) stage.status = 'completed';
      else stage.status = 'queued';

      const stageTasksWithMetrics = stage.tasks.filter(t => t.metrics);
      if (stageTasksWithMetrics.length > 0) {
        stage.minStart = Math.min(...stageTasksWithMetrics.map(t => t.metrics.dependency_wait || 0));
        stage.maxEnd = Math.max(...stageTasksWithMetrics.map(t => (t.metrics.dependency_wait || 0) + (t.metrics.queue_wait || 0) + (t.metrics.execution_duration || 0)));
      } else {
        stage.minStart = 0; stage.maxEnd = 0;
      }
      stage.hasSlowest = stage.tasks.some(t => t.is_slowest_compute);
      stage.hasBusy = stage.tasks.some(t => (t.metrics?.queue_wait || 0) > 1);
    });

    const result = STAGE_ORDER.map(s => buckets[s]).filter(b => b.tasks.length > 0 || b.status === 'running');
    
    result.forEach(stage => {
      stage.execProp = (stage.totalExec / totalPipelineExecTime) * 100;
      stage.waitProp = (stage.totalWait / totalPipelineExecTime) * 100;
      stage.depWaitProp = (stage.totalDepWait / totalPipelineExecTime) * 100;
      stage.qWaitProp = (stage.totalQWait / totalPipelineExecTime) * 100;
      if (stage.execProp < 5 && stage.totalExec > 0) stage.execProp = 5; 
      if (stage.waitProp < 2 && stage.totalWait > 0) stage.waitProp = 2;
    });

    return result;
  }, [tasks, tick]);

  const selectedItem = useMemo(() => {
    if (!selectedItemState) return null;
    if (selectedItemState.type === 'stage') {
      const s = stagesData.find(st => String(st.name) === String(selectedItemState.id));
      return s ? { type: 'stage', data: s } : null;
    } else {
      let tFound = null;
      stagesData.forEach(st => {
        const found = st.tasks.find(t => String(t.id) === String(selectedItemState.id));
        if (found) tFound = found;
      });
      return tFound ? { type: 'task', data: tFound } : null;
    }
  }, [selectedItemState, stagesData]);

  const overallProgress = useMemo(() => {
    if (!tasks || tasks.length === 0) return 0;
    const completed = tasks.filter(t => t.status === 'completed').length;
    return Math.round((completed / tasks.length) * 100);
  }, [tasks]);

  const activeStage = useMemo(() => {
    return stagesData.find(s => s.status === 'running') || stagesData[stagesData.length - 1];
  }, [stagesData]);

  const { initialNodes, initialEdges } = useMemo(() => {
    if (!tasks) return { initialNodes: [], initialEdges: [] };
    
    const allEnhanced = [];
    stagesData.forEach(s => {
      s.tasks.forEach(t => allEnhanced.push({ ...t, stageAssigned: s.name }));
    });

    const totalLatency = metrics?.total_latency_seconds || 1;
    const direction = 'TB';

    const nds = allEnhanced.map(t => {
      const metric = metrics?.node_weights?.[t.id] ?? null;
      return {
        id: String(t.id || Math.random()),
        type: 'customDagNode',
        data: { ...t, metric, totalLatency, direction },
        position: { x: 0, y: 0 }
      };
    });

    const nodeIds = new Set(nds.map(n => n.id));
    const eds = [];
    const hasAnyCompleted = allEnhanced.some(t => t.status === 'completed');
    const cp = (metrics?.critical_path || []).map(String);
    const isCritEdge = (s, t) => { const i = cp.indexOf(String(s)); return i >= 0 && cp[i+1] === String(t); };
    
    allEnhanced.forEach(t => {
      let deps = t.dependencies || [];
      if (typeof deps === 'string') {
        try { deps = JSON.parse(deps); } catch (e) { deps = []; }
      }
      if (Array.isArray(deps)) {
        deps.forEach(dep => {
          if (nodeIds.has(String(dep)) && nodeIds.has(String(t.id))) {
            const isCrit = hasAnyCompleted && isCritEdge(dep, t.id);
            const targetRunning = t.status === 'running';
            eds.push({
              id: `e-${dep}-${t.id}`,
              source: String(dep),
              target: String(t.id),
              type: 'smoothstep',
              animated: isCrit || targetRunning,
              style: { 
                stroke: isCrit ? '#ef4444' : '#475569', 
                strokeWidth: isCrit ? 3 : 1.5,
                strokeDasharray: (targetRunning && !isCrit) ? '5,5' : undefined
              },
              markerEnd: { type: MarkerType.ArrowClosed, color: isCrit ? '#ef4444' : '#475569' }
            });
          }
        });
      }
    });

    if (eds.length === 0 && nds.length > 1) {
      for(let i = 0; i < nds.length - 1; i++) {
        const isCrit = hasAnyCompleted && isCritEdge(nds[i].id, nds[i+1].id);
        const targetRunning = nds[i+1].data.status === 'running';
        eds.push({
          id: `e-${nds[i].id}-${nds[i+1].id}`,
          source: nds[i].id,
          target: nds[i+1].id,
          type: 'smoothstep',
          animated: isCrit || targetRunning,
          style: { 
            stroke: isCrit ? '#ef4444' : '#475569', 
            strokeWidth: isCrit ? 3 : 1.5,
            strokeDasharray: (targetRunning && !isCrit) ? '5,5' : undefined
          },
          markerEnd: { type: MarkerType.ArrowClosed, color: isCrit ? '#ef4444' : '#475569' }
        });
      }
    }

    const result = getLayoutedElements(nds, eds, direction);
    return { initialNodes: result.nodes, initialEdges: result.edges };
  }, [stagesData, tasks, metrics]);

  const toggleStage = (stageName) => {
    setExpandedStages(prev => ({ ...prev, [stageName]: !prev[stageName] }));
  };

  const displayNodes = useMemo(() => {
    return initialNodes.map(n => {
       let isDimmed = false;
       let isHovered = false;
       if (hoveredNodeId) {
          let ancestors = new Set([hoveredNodeId]);
          let descendants = new Set([hoveredNodeId]);
          let changed = true;
          while(changed) {
             changed = false;
             initialEdges.forEach(e => {
                if (descendants.has(e.source) && !descendants.has(e.target)) { descendants.add(e.target); changed = true; }
                if (ancestors.has(e.target) && !ancestors.has(e.source)) { ancestors.add(e.source); changed = true; }
             });
          }
          const highlightedNodes = new Set([...ancestors, ...descendants]);
          isHovered = n.id === hoveredNodeId;
          isDimmed = !highlightedNodes.has(n.id);
       }
       return { ...n, data: { ...n.data, isHovered, isDimmed } };
    });
  }, [initialNodes, initialEdges, hoveredNodeId]);

  const displayEdges = useMemo(() => {
    return initialEdges.map(e => {
       let isDimmed = false;
       if (hoveredNodeId) {
          let ancestors = new Set([hoveredNodeId]);
          let descendants = new Set([hoveredNodeId]);
          let changed = true;
          while(changed) {
             changed = false;
             initialEdges.forEach(ee => {
                if (descendants.has(ee.source) && !descendants.has(ee.target)) { descendants.add(ee.target); changed = true; }
                if (ancestors.has(ee.target) && !ancestors.has(ee.source)) { ancestors.add(ee.source); changed = true; }
             });
          }
          const highlightedNodes = new Set([...ancestors, ...descendants]);
          isDimmed = !(highlightedNodes.has(e.source) && highlightedNodes.has(e.target));
       }
       return { ...e, style: { ...e.style, opacity: isDimmed ? 0.2 : 1 } };
    });
  }, [initialEdges, hoveredNodeId]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%', flex: 1, minHeight: 0, background: '#0a0a0f', color: '#e2e8f0', fontFamily: 'Inter, sans-serif', position: 'relative' }}>
      <style>{visualizerStyles}</style>
      
      {/* Top Header / Overall Progress */}
      <div style={{ padding: '24px 32px', borderBottom: '1px solid #1f1f2e', background: '#0d0d14' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <h1 style={{ fontSize: '1.25rem', fontWeight: 600, margin: '0 0 8px 0', color: '#fff' }}>Runtime Orchestration</h1>
          </div>
          
          <div style={{ display: 'flex', background: '#12121a', borderRadius: '8px', padding: '4px', border: '1px solid #1f1f2e' }}>
            <button 
              onClick={() => setViewMode('timeline')}
              style={{
                display: 'flex', alignItems: 'center', gap: '6px',
                padding: '8px 16px', borderRadius: '6px', border: 'none', cursor: 'pointer',
                background: viewMode === 'timeline' ? '#1e1e2d' : 'transparent',
                color: viewMode === 'timeline' ? '#fff' : '#64748b',
                fontWeight: viewMode === 'timeline' ? 600 : 400,
                transition: 'all 0.2s'
              }}
            >
              <LayoutList size={16} /> Timeline View
            </button>
            <button 
              onClick={() => setViewMode('graph')}
              style={{
                display: 'flex', alignItems: 'center', gap: '6px',
                padding: '8px 16px', borderRadius: '6px', border: 'none', cursor: 'pointer',
                background: viewMode === 'graph' ? '#1e1e2d' : 'transparent',
                color: viewMode === 'graph' ? '#fff' : '#64748b',
                fontWeight: viewMode === 'graph' ? 600 : 400,
                transition: 'all 0.2s'
              }}
            >
              <GitBranch size={16} /> Graph View
            </button>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ flex: 1, height: '6px', background: '#1f1f2e', borderRadius: '4px', overflow: 'hidden' }}>
            <div style={{ 
              height: '100%', 
              background: '#3b82f6', 
              width: `${overallProgress}%`,
              transition: 'width 0.5s ease',
              boxShadow: '0 0 10px rgba(59, 130, 246, 0.5)'
            }} />
          </div>
          <div style={{ fontSize: '0.875rem', color: '#94a3b8', fontWeight: 500, minWidth: '140px', textAlign: 'right' }}>
            {overallProgress}% Complete • {activeStage?.name ? STAGE_LABELS[activeStage.name] : 'Done'}
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden', position: 'relative' }}>
        {viewMode === 'timeline' ? (
          <>
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', borderRight: '1px solid #1f1f2e', overflow: 'hidden' }}>
              {(() => {
                const totalSecs = metrics?.total_latency_seconds || 1;
                const tickInterval = Math.max(1, Math.ceil(totalSecs / 10));
                const ticks = [];
                for (let i = 0; i <= totalSecs; i += tickInterval) ticks.push(i);
                if (ticks[ticks.length - 1] < totalSecs) ticks.push(totalSecs);
                
                return (
                  <div style={{ padding: '16px 32px 12px', background: '#09090e', borderBottom: '1px solid #1f1f2e', zIndex: 10 }}>
                    <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', marginBottom: '10px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '14px', fontSize: '0.75rem', color: '#94a3b8' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <div style={{ width: '8px', height: '8px', borderRadius: '2px', background: '#ef4444' }} /> Critical path
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <div style={{ width: '8px', height: '8px', borderRadius: '2px', background: '#f59e0b' }} /> Queued behind worker
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <div style={{ width: '8px', height: '8px', borderRadius: '2px', background: 'rgba(239, 68, 68, 0.2)', border: '1px solid #ef4444' }} /> Slowest compute
                        </div>
                      </div>
                    </div>
                    <div style={{ width: '100%', height: '20px', position: 'relative', color: '#64748b', fontSize: '0.75rem' }}>
                      {hasMetrics && ticks.map(t => (
                        <div key={t} style={{ position: 'absolute', left: `${(t / totalSecs) * 100}%`, transform: 'translateX(-50%)', bottom: '2px' }}>
                          {t % 1 !== 0 ? t.toFixed(2) : t}s
                        </div>
                      ))}
                      {!hasMetrics && <span style={{ position: 'absolute', right: 0, bottom: '2px' }}>—</span>}
                    </div>
                  </div>
                );
              })()}
              <div style={{ flex: 1, overflowY: 'auto', padding: '32px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', maxWidth: '100%', margin: '0 auto' }}>
                {stagesData.map((stage, idx) => {
                  const isRunning = stage.status === 'running';
                  const isExpanded = expandedStages[stage.name];
                  const IconComp = STAGE_ICONS[stage.name] || FileText;
                  
                  return (
                    <div key={stage.name} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      <div 
                        onClick={() => setSelectedItemState({ type: 'stage', id: stage.name })}
                        className={isRunning ? 'stage-running' : ''}
                        style={{
                          background: isRunning ? '#111827' : '#0d0d14',
                          border: `1px solid ${isRunning ? '#3b82f6' : '#1f1f2e'}`,
                          borderRadius: '12px',
                          padding: '20px',
                          cursor: 'pointer',
                          position: 'relative',
                          overflow: 'hidden',
                          transition: 'all 0.2s',
                          borderLeft: stage.criticalPath ? '4px solid #ef4444' : `4px solid transparent`,
                        }}
                      >
                        {isRunning && (
                          <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: '100%', background: 'linear-gradient(90deg, rgba(59,130,246,0.1) 0%, rgba(0,0,0,0) 100%)', pointerEvents: 'none' }} />
                        )}

                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'relative', zIndex: 1 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                            <div 
                              onClick={(e) => { e.stopPropagation(); toggleStage(stage.name); }}
                              style={{ padding: '4px', background: '#1e1e2d', borderRadius: '6px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                            >
                              {isExpanded ? <ChevronDown size={16} color="#94a3b8" /> : <ChevronRight size={16} color="#94a3b8" />}
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <IconComp size={18} color="#94a3b8" />
                              <h3 style={{ margin: 0, fontSize: '1.125rem', fontWeight: 600, color: isRunning ? '#fff' : '#e2e8f0', letterSpacing: '0.02em' }}>
                                {STAGE_LABELS[stage.name]}
                              </h3>
                              {stage.hasSlowest && (
                                <span style={{ fontSize: '0.65rem', background: 'rgba(239, 68, 68, 0.2)', color: '#ef4444', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>
                                  Slowest compute
                                </span>
                              )}
                              {stage.tasks.some(t => t.is_worker_busy) && (
                                <span style={{ fontSize: '0.65rem', background: 'rgba(245, 158, 11, 0.2)', color: '#f59e0b', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>
                                  Worker busy
                                </span>
                              )}
                            </div>
                            <div style={{ 
                              padding: '4px 10px', 
                              borderRadius: '20px', 
                              fontSize: '0.75rem', 
                              fontWeight: 600,
                              textTransform: 'uppercase',
                              background: `${getStatusColor(stage.status)}22`,
                              color: getStatusColor(stage.status),
                              display: 'flex',
                              alignItems: 'center',
                              gap: '6px'
                            }}>
                              <StatusIcon status={stage.status} size={12} />
                              {stage.status}
                            </div>
                          </div>
                          
                          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', minWidth: '100px' }}>
                            <div style={{ fontSize: '0.875rem', color: '#64748b', fontFamily: 'monospace' }}>
                              {stage.tasks.length} {stage.tasks.length === 1 ? 'task' : 'tasks'}
                            </div>
                            <div style={{ fontSize: '0.75rem', color: '#cbd5e1', fontWeight: 500 }}>
                              Span: {formatDuration((stage.maxEnd - stage.minStart) * 1000, hasMetrics)}
                            </div>
                          </div>
                        </div>

                        <div style={{ padding: '0 0', marginTop: '16px' }}>
                           <div style={{ width: '100%', height: '12px', background: '#1f1f2e', borderRadius: '6px', position: 'relative', overflow: 'hidden' }}>
                             {hasMetrics && stage.tasks.map(task => {
                               const totalLat = metrics?.total_latency_seconds || 1;
                               const tLeft = Math.min(100, ((task.metrics?.dependency_wait || 0) / totalLat) * 100);
                               const tQW = Math.min(100 - tLeft, ((task.metrics?.queue_wait || 0) / totalLat) * 100);
                               const tExW = Math.min(100 - tLeft - tQW, Math.max(0.5, ((task.metrics?.execution_duration || 0) / totalLat) * 100));
                               return (
                                 <div key={task.id} style={{ position: 'absolute', left: `${tLeft}%`, display: 'flex', height: '100%', width: '100%' }}>
                                    <div style={{ width: `${tQW}%`, background: '#475569', opacity: 0.8 }} title="Queue Wait" />
                                    <div style={{ width: `${tExW}%`, background: getStatusColor(task.status), opacity: 0.8 }} title="Execution" />
                                 </div>
                               );
                             })}
                           </div>
                        </div>
                      </div>

                      {isExpanded && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          {stage.tasks.map(task => (
                            <div 
                              key={task.id}
                              onClick={(e) => { e.stopPropagation(); setSelectedItemState({ type: 'task', id: task.id }); }}
                              style={{
                                background: '#0d0d14',
                                border: '1px solid #1f1f2e',
                                borderRadius: '8px',
                                padding: '12px 20px',
                                display: 'flex',
                                flexDirection: 'column',
                                gap: '12px',
                                cursor: 'pointer',
                                transition: 'background 0.2s',
                                borderLeft: task.is_critical_path ? '3px solid #ef4444' : '1px solid #1f1f2e'
                              }}
                              onMouseOver={(e) => e.currentTarget.style.background = '#12121a'}
                              onMouseOut={(e) => e.currentTarget.style.background = '#0d0d14'}
                            >
                              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingLeft: '48px' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                  <StatusIcon status={task.status} size={14} />
                                  <span style={{ fontSize: '0.875rem', fontWeight: 500, color: '#cbd5e1' }}>
                                    {task.task_type || task.type || task.id}
                                  </span>
                                  {task.is_slowest_compute && (
                                    <span style={{ fontSize: '0.65rem', background: 'rgba(239, 68, 68, 0.2)', color: '#ef4444', padding: '2px 6px', borderRadius: '4px', fontWeight: 600, border: '1px solid #ef4444' }}>
                                      Slowest compute
                                    </span>
                                  )}
                                  {(task.metrics?.queue_wait > 1) && (
                                    <span style={{ fontSize: '0.65rem', background: 'rgba(245, 158, 11, 0.2)', color: '#f59e0b', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>
                                      {task.is_worker_busy 
                                        ? `Queued ${task.metrics.queue_wait.toFixed(1)}s (worker busy: ${task.assigned_worker_id || task.worker || 'auto'})` 
                                        : `Queued ${task.metrics.queue_wait.toFixed(1)}s`}
                                    </span>
                                  )}
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '24px', fontFamily: 'monospace', fontSize: '0.75rem', color: '#64748b' }}>
                                  <span>Worker: {task.assigned_worker_id || task.worker || 'auto'}</span>
                                  <span>Exec: {formatDuration(task.computedExec, hasMetrics)}</span>
                                </div>
                              </div>
                              
                              <div style={{ padding: '0 0' }}>
                                <div style={{ width: '100%', height: '8px', background: '#12121a', borderRadius: '4px', position: 'relative' }}>
                                  {hasMetrics && (() => {
                                    const totalLat = metrics?.total_latency_seconds || 1;
                                    const tLeft = Math.min(100, ((task.metrics?.dependency_wait || 0) / totalLat) * 100);
                                    const tQW = Math.min(100 - tLeft, ((task.metrics?.queue_wait || 0) / totalLat) * 100);
                                    const tExW = Math.min(100 - tLeft - tQW, Math.max(0.5, ((task.metrics?.execution_duration || 0) / totalLat) * 100));
                                    return (
                                      <div style={{ position: 'absolute', left: `${tLeft}%`, display: 'flex', height: '100%', width: '100%' }}>
                                        <div style={{ width: `${tQW}%`, background: '#475569' }} />
                                        <div style={{ width: `${tExW}%`, background: getStatusColor(task.status) }} />
                                      </div>
                                    );
                                  })()}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      {idx < stagesData.length - 1 && (
                        <div style={{ display: 'flex', justifyContent: 'center', padding: '8px 0', position: 'relative' }}>
                          <div style={{ position: 'absolute', top: 0, bottom: 0, left: '50%', width: '2px', background: '#2a2a35', zIndex: 0 }} />
                          <div style={{ 
                            background: '#1e1e2d', border: '1px solid #3b82f6', borderRadius: '16px', 
                            padding: '6px 14px', fontSize: '0.75rem', color: '#e2e8f0', fontWeight: 600,
                            display: 'flex', alignItems: 'center', gap: '6px', zIndex: 1,
                            cursor: 'pointer', boxShadow: '0 0 10px rgba(59, 130, 246, 0.2)'
                          }}>
                            <Database size={12} style={{ color: '#3b82f6' }} />
                            Data Artifact
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

            <div className={`detail-panel ${selectedItemState ? 'open' : ''}`}>
              {!selectedItem ? (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#64748b', gap: '16px' }}>
                  <LayoutList size={48} opacity={0.2} />
                  <p>Select a stage or task to view details</p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
                  
                  <div style={{ position: 'relative' }}>
                    <button 
                      onClick={() => setSelectedItemState(null)}
                      style={{ position: 'absolute', top: 0, right: 0, background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: '4px' }}
                      className="mobile-only-close" // Just generic style, can use CSS or just keep it simple
                    >
                      <X size={20} />
                    </button>
                    <div style={{ fontSize: '0.75rem', color: '#3b82f6', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.05em', marginBottom: '8px' }}>
                      {selectedItem.type === 'stage' ? 'Stage Details' : 'Task Details'}
                    </div>
                    <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#fff', margin: '0 0 12px 0' }}>
                      {selectedItem.type === 'stage' 
                        ? STAGE_LABELS[selectedItem.data.name] 
                        : (selectedItem.data.task_type || selectedItem.data.type || selectedItem.data.id)}
                    </h2>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <StatusIcon status={selectedItem.data.status} size={16} />
                      <span style={{ fontSize: '0.875rem', color: '#cbd5e1', textTransform: 'capitalize' }}>
                        {selectedItem.data.status}
                      </span>
                    </div>
                  </div>

                    {(() => {
                      const failedTask = selectedItem.type === 'stage' 
                        ? selectedItem.data.tasks?.find(t => t.status === 'failed') 
                        : (selectedItem.data.status === 'failed' ? selectedItem.data : null);
                      const errMsg = failedTask?.error || failedTask?.error_message || failedTask?.message;
                      
                      if (errMsg) {
                        return (
                          <div style={{ background: '#0d0d14', border: '1px solid #ef4444', borderRadius: '12px', padding: '20px', marginBottom: '20px' }}>
                            <h4 style={{ fontSize: '0.875rem', fontWeight: 600, color: '#ef4444', margin: '0 0 12px 0' }}>Failure Reason</h4>
                            <div style={{ fontSize: '0.8125rem', color: '#f87171', background: 'rgba(239, 68, 68, 0.1)', padding: '12px', borderRadius: '6px', fontFamily: 'monospace', whiteSpace: 'pre-wrap', userSelect: 'all', marginBottom: '16px' }}>
                              {errMsg}
                            </div>
                            {onRetryTask && (
                              <button
                                onClick={() => onRetryTask(failedTask.id)}
                                style={{
                                  background: 'rgba(239, 68, 68, 0.15)',
                                  border: '1px solid rgba(239, 68, 68, 0.3)',
                                  color: '#ef4444',
                                  padding: '8px 16px',
                                  borderRadius: '6px',
                                  fontSize: '0.85rem',
                                  fontWeight: 600,
                                  cursor: 'pointer',
                                  width: '100%',
                                  transition: 'all 0.2s',
                                }}
                                onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(239, 68, 68, 0.25)'; }}
                                onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(239, 68, 68, 0.15)'; }}
                              >
                                Retry Task
                              </button>
                            )}
                          </div>
                        );
                      }
                      return null;
                    })()}

                    <div style={{ background: '#0d0d14', border: '1px solid #1f1f2e', borderRadius: '12px', padding: '20px' }}>
                      <h4 style={{ fontSize: '0.875rem', fontWeight: 600, color: '#e2e8f0', margin: '0 0 16px 0' }}>Timing Breakdown</h4>
                      {!metrics ? (
                        <div style={{ fontSize: '0.8125rem', color: '#ef4444', background: 'rgba(239, 68, 68, 0.1)', padding: '8px 12px', borderRadius: '6px' }}>
                          Timing metrics unavailable.
                        </div>
                      ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                          {(() => {
                            const item = selectedItem;
                            const isStage = item.type === 'stage';
                            const status = isStage ? item.data.status : item.data.status;
                            const isNotStarted = status === 'queued' || status === 'pending' || status === 'blocked';

                            let startStr = '-';
                            let endStr = '-';

                            if (!isNotStarted) {
                              if (isStage) {
                                const tasksList = item.data.tasks || [];
                                const startTask = tasksList.find(t => t.started_at);
                                if (startTask?.started_at) {
                                  startStr = formatIST(startTask.started_at);
                                }
                                if (status === 'running') {
                                  endStr = 'In progress';
                                } else {
                                  const endTask = [...tasksList].reverse().find(t => t.completed_at || t.updated_at);
                                  if (endTask?.completed_at || endTask?.updated_at) {
                                    endStr = formatIST(endTask.completed_at || endTask.updated_at);
                                  }
                                }
                              } else {
                                if (item.data.started_at) {
                                  startStr = formatIST(item.data.started_at);
                                }
                                if (status === 'running') {
                                  endStr = 'In progress';
                                } else if (item.data.completed_at || item.data.updated_at) {
                                  endStr = formatIST(item.data.completed_at || item.data.updated_at);
                                }
                              }
                            }

                            return (
                              <>
                                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem' }}>
                                  <span style={{ color: '#94a3b8' }}>Started At (IST)</span>
                                  <span style={{ color: '#fff', fontFamily: 'monospace' }}>{startStr}</span>
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem' }}>
                                  <span style={{ color: '#94a3b8' }}>Completed At (IST)</span>
                                  <span style={{ color: '#fff', fontFamily: 'monospace' }}>{endStr}</span>
                                </div>
                              </>
                            );
                          })()}
                          <div style={{ height: '1px', background: '#1f1f2e', margin: '4px 0' }} />
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem' }}>
                          <span style={{ color: '#94a3b8' }}>{selectedItem.type === 'stage' ? 'Total Span' : 'Dependency Wait'}</span>
                          <span style={{ color: '#fff', fontFamily: 'monospace' }}>
                            {formatDuration(selectedItem.type === 'stage' ? ((selectedItem.data.maxEnd - selectedItem.data.minStart) * 1000) : (selectedItem.data.metrics?.dependency_wait * 1000 || 0), hasMetrics)}
                          </span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem' }}>
                          <span style={{ color: '#94a3b8' }}>Queue Wait Time</span>
                          <span style={{ color: '#fff', fontFamily: 'monospace' }}>
                            {formatDuration(selectedItem.type === 'stage' ? selectedItem.data.totalQWait : (selectedItem.data.metrics?.queue_wait * 1000 || 0), hasMetrics)}
                          </span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem' }}>
                          <span style={{ color: '#94a3b8' }}>Execution Time</span>
                          <span style={{ color: '#fff', fontFamily: 'monospace' }}>
                            {formatDuration(selectedItem.type === 'stage' ? selectedItem.data.totalExec : (selectedItem.data.metrics?.execution_duration * 1000 || 0), hasMetrics)}
                          </span>
                        </div>
                        {(selectedItem.type === 'task' && selectedItem.data.metrics?.recovery_delay > 0) && (
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem' }}>
                            <span style={{ color: '#ef4444' }}>Recovery Delay</span>
                            <span style={{ color: '#ef4444', fontFamily: 'monospace' }}>
                              {formatDuration(selectedItem.data.metrics.recovery_delay * 1000, hasMetrics)}
                            </span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {selectedItem.type === 'task' && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                      <div style={{ background: '#0d0d14', border: '1px solid #1f1f2e', borderRadius: '12px', padding: '20px' }}>
                        <h4 style={{ fontSize: '0.875rem', fontWeight: 600, color: '#e2e8f0', margin: '0 0 12px 0' }}>Inputs</h4>
                        {selectedItem.data.input_artifact_ids ? (
                          <div style={{ fontSize: '0.8125rem', color: '#94a3b8', background: '#12121a', padding: '8px 12px', borderRadius: '6px', fontFamily: 'monospace' }}>
                            {selectedItem.data.input_artifact_ids}
                          </div>
                        ) : (
                          <div style={{ fontSize: '0.8125rem', color: '#64748b' }}>No inputs recorded.</div>
                        )}
                      </div>

                      <div style={{ background: '#0d0d14', border: '1px solid #1f1f2e', borderRadius: '12px', padding: '20px' }}>
                        <h4 style={{ fontSize: '0.875rem', fontWeight: 600, color: '#e2e8f0', margin: '0 0 12px 0' }}>Outputs</h4>
                        {selectedItem.data.output_artifact_ids ? (
                          <div style={{ fontSize: '0.8125rem', color: '#94a3b8', background: '#12121a', padding: '8px 12px', borderRadius: '6px', fontFamily: 'monospace' }}>
                            {selectedItem.data.output_artifact_ids}
                          </div>
                        ) : (
                          <div style={{ fontSize: '0.8125rem', color: '#64748b' }}>No outputs recorded.</div>
                        )}
                      </div>

                      <div style={{ background: '#0d0d14', border: '1px solid #1f1f2e', borderRadius: '12px', padding: '20px' }}>
                        <h4 style={{ fontSize: '0.875rem', fontWeight: 600, color: '#e2e8f0', margin: '0 0 12px 0' }}>System Execution</h4>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem' }}>
                            <span style={{ color: '#94a3b8' }}>Worker ID</span>
                            <span style={{ color: '#fff', fontFamily: 'monospace' }}>{selectedItem.data.assigned_worker_id || selectedItem.data.worker || 'System Default'}</span>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem' }}>
                            <span style={{ color: '#94a3b8' }}>Retries</span>
                            <span style={{ color: '#fff', fontFamily: 'monospace' }}>{selectedItem.data.retry_count || 0}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                </div>
              )}
            </div>
          </>
        ) : (
          <div style={{ flex: 1, minHeight: 0, position: 'relative', background: '#0a0a0f', width: '100%', height: '100%' }}>
             {/* Legend (from timeline) */}
              <div style={{ position: 'absolute', top: 20, left: 20, zIndex: 4, display: 'flex', gap: '16px', fontSize: '0.75rem', color: '#94a3b8', background: 'rgba(10,10,15,0.8)', padding: '8px 12px', borderRadius: '6px', border: '1px solid #1f1f2e' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><div style={{ width: 8, height: 8, borderRadius: '50%', background: '#ef4444' }} />Critical path</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><div style={{ width: 8, height: 8, borderRadius: '50%', background: '#f59e0b' }} />Queued behind worker</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><div style={{ width: 8, height: 8, borderRadius: '50%', border: '1px solid #ef4444', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><X size={6} color="#ef4444" /></div>Slowest compute</div>
              </div>
              <ReactFlow 
                key={initialNodes.length}
                nodes={displayNodes}
                edges={displayEdges}
                nodeTypes={nodeTypes}
                onInit={(instance) => {
                   setRfInstance(instance);
                   setTimeout(() => {
                      window.requestAnimationFrame(() => instance.fitView({ padding: 0.1, minZoom: 0.75, maxZoom: 1 }));
                   }, 100);
                }}
                onNodeClick={(_, node) => setSelectedItemState({ type: 'task', id: node.id })}
                onNodeMouseEnter={(_, node) => setHoveredNodeId(node.id)}
                onNodeMouseLeave={() => setHoveredNodeId(null)}
                minZoom={0.1}
                maxZoom={1.5}
                panOnScroll={true}
                zoomOnScroll={false}
              >
                <Background color="#1f1f2e" gap={20} size={1} />
                <Controls showInteractive={false} style={{ background: '#12121a', border: '1px solid #1f1f2e', fill: '#fff' }} />
                <MiniMap 
                  style={{ background: '#12121a', border: '1px solid #1f1f2e', borderRadius: '8px' }}
                  nodeColor={(node) => {
                     const status = node.data.status || 'pending';
                     if (status === 'completed') return '#22c55e';
                     if (status === 'failed') return '#ef4444';
                     if (status === 'running') return '#3b82f6';
                     return '#475569';
                  }}
                  maskColor="rgba(10, 10, 15, 0.7)"
                />
              </ReactFlow>
          </div>
        )}

      </div>
    </div>
  );
};

export default PipelineVisualizer;
