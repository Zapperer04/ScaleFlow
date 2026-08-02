import React from 'react';
import { usePipeline } from '../../../contexts/PipelineContext';

/**
 * PipelineDAG Component
 *
 * Visualizes the frozen MR-RAG pipeline DAG dynamically driven by backend tasks and edges
 * returned from GET /pipelines/{id}/dag or task list.
 *
 * Status colors:
 * - pending / queued: Grey (#64748b)
 * - running: Blue (#3b82f6) + animated stroke glow
 * - completed: Green (#10b981)
 * - failed: Red (#ef4444)
 * - retrying / paused: Amber (#f59e0b)
 */


export const PipelineDAG = ({ tasks = [], artifacts = [], dagNodes = [], dagEdges = [], onSelectNode, selectedNodeId }) => {
  const {
    selectedTaskId, setSelectedTaskId,
    setSelectedTraceId, setSelectedWorkerId,
    replayMode,
    replayIndex,
    replaySnapshots,
    selectedSnapshotAIndex,
    selectedSnapshotBIndex,
    comparisonMode,
    snapshotDiff,
    performanceModel,
    forecastModel,
    advisorModel
  } = usePipeline();

  const defaultNodes = [
    { id: 'upload',        name: 'Upload',               ref: 'upload',              x: 40,  y: 100 },
    { id: 'preprocess',    name: 'Preprocessing',        ref: 'preprocess_document', x: 160, y: 100 },
    { id: 'parse',         name: 'VLM Parsing',          ref: 'parse_document',      x: 290, y: 100 },
    { id: 'graph',         name: 'document_graph.json',  ref: 'build_graph',         x: 430, y: 50 },
    { id: 'chunk',         name: 'graph_chunks.json',    ref: 'chunk_document',      x: 430, y: 150 },
    { id: 'embedding',     name: 'Embedding Gen',        ref: 'generate_embeddings', x: 570, y: 100 },
    { id: 'bm25',          name: 'BM25 Index',           ref: 'index_bm25',          x: 700, y: 100 },
    { id: 'retrieval',     name: 'Hybrid Retrieval',     ref: 'query_pipeline',      x: 830, y: 100 },
    { id: 'ready',         name: 'Retrieval Ready',      ref: 'ready',               x: 950, y: 100 }
  ];

  const getTaskDiffForRef = (refName) => {
    if (!comparisonMode || !snapshotDiff || !replaySnapshots) return null;
    const task = tasks.find(t => t.type === refName || t.task_type === refName);
    if (!task) return null;
    const idStr = String(task.id);
    const hasDiff = snapshotDiff.tasks.some(d => String(d.taskId) === idStr);
    if (!hasDiff) return null;

    const snapA = replaySnapshots[selectedSnapshotAIndex];
    const snapB = replaySnapshots[selectedSnapshotBIndex];
    const taskA = snapA?.taskStates?.[idStr] || { status: 'pending', workerId: null };
    const taskB = snapB?.taskStates?.[idStr] || { status: 'pending', workerId: null };

    return {
      before: taskA,
      after: taskB
    };
  };

  const getPerformanceMetricsForTask = (taskId) => {
    if (!performanceModel?.performance?.timeline) return null;
    const taskSegs = performanceModel.performance.timeline.filter(s => String(s.task_id) === String(taskId));
    if (taskSegs.length === 0) return null;
    
    const totalExec = taskSegs.reduce((acc, s) => acc + s.duration_ms, 0);
    const totalWait = taskSegs.reduce((acc, s) => acc + (s.queue_wait_ms || 0), 0);
    const retries = taskSegs.length - 1;
    return {
      execution_ms: totalExec,
      queue_wait_ms: totalWait,
      retries
    };
  };

  const buildTooltipText = (node, diffInfo, task) => {
    if (diffInfo) {
      let lines = [`Diff Details for ${node.name}:`];
      if (diffInfo.before.status !== diffInfo.after.status) {
        lines.push(`• Status: ${diffInfo.before.status} ➔ ${diffInfo.after.status}`);
      }
      if (diffInfo.before.workerId !== diffInfo.after.workerId) {
        lines.push(`• Worker: ${diffInfo.before.workerId || 'None'} ➔ ${diffInfo.after.workerId || 'None'}`);
      }
      if (diffInfo.before.retryCount !== diffInfo.after.retryCount) {
        lines.push(`• Retry: ${diffInfo.before.retryCount} ➔ ${diffInfo.after.retryCount}`);
      }
      if (diffInfo.before.queue !== diffInfo.after.queue) {
        lines.push(`• Queue: ${diffInfo.before.queue || 'None'} ➔ ${diffInfo.after.queue || 'None'}`);
      }
      if (diffInfo.before.progress !== diffInfo.after.progress) {
        lines.push(`• Progress: ${diffInfo.before.progress || 'None'} ➔ ${diffInfo.after.progress || 'None'}`);
      }
      return lines.join('\n');
    }
    if (task) {
      const perf = getPerformanceMetricsForTask(task.id);
      let base = `${node.name}
Status: ${task.status}
Worker: ${task.assigned_worker_id || 'None'}
Retries: ${task.retry_count || 0}`;
      
      if (perf) {
        base += `\nExecution Duration: ${perf.execution_ms}ms\nQueue Wait: ${perf.queue_wait_ms}ms`;
      }
      const isFuture = forecastModel?.forecast?.future_tasks?.some(ft => String(ft.status === 'running' || ft.task_id === task.id));
      if (isFuture) {
        const ft = forecastModel.forecast.future_tasks.find(ft => String(ft.task_id) === String(task.id));
        if (ft) {
          base += `\n[Forecast] Predicted Start: ${Math.round(ft.predicted_start_ms)}ms`;
          base += `\n[Forecast] Predicted End: ${Math.round(ft.predicted_end_ms)}ms`;
          base += `\n[Forecast] Status: Predicted ${ft.status}`;
        }
      }
      return base;
    }
    return node.name;
  };

  const getTaskForRef = (refName) => {
    if (replayMode && replaySnapshots && replayIndex >= 0 && replayIndex < replaySnapshots.length) {
      const snapshot = replaySnapshots[replayIndex];
      const matchingTaskId = Object.keys(snapshot.taskStates).find(id => {
        const originalTask = tasks.find(t => String(t.id) === id);
        return originalTask && (originalTask.type === refName || originalTask.task_type === refName);
      });
      if (matchingTaskId) {
        const t = tasks.find(t => String(t.id) === matchingTaskId);
        return {
          ...t,
          status: snapshot.taskStates[matchingTaskId].status,
          assigned_worker_id: snapshot.taskStates[matchingTaskId].workerId
        };
      }
    }
    return tasks.find(t => t.type === refName || t.task_type === refName);
  };

  const isNodeValidationFailed = (task) => {
    if (!task || !task.artifacts) return false;
    return task.artifacts.some(art => art.metadata_json?.validation?.is_valid === false);
  };

  const getStatusColor = (status, isFailed) => {
    if (isFailed) return '#ef4444';
    switch (status) {
      case 'completed': return '#10b981';
      case 'running': return '#3b82f6';
      case 'failed': return '#ef4444';
      case 'retrying': return '#f59e0b';
      case 'paused': return '#f59e0b';
      default: return '#64748b';
    }
  };

  const getStatusBg = (status, isFailed) => {
    if (isFailed) return 'rgba(239, 68, 68, 0.1)';
    switch (status) {
      case 'completed': return 'rgba(16, 185, 129, 0.1)';
      case 'running': return 'rgba(59, 130, 246, 0.1)';
      case 'failed': return 'rgba(239, 68, 68, 0.1)';
      case 'retrying': return 'rgba(245, 158, 11, 0.1)';
      case 'paused': return 'rgba(245, 158, 11, 0.1)';
      default: return 'rgba(100, 116, 139, 0.05)';
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="overflow-x-auto custom-scrollbar border border-slate-800 rounded-xl bg-slate-950/20 p-6 flex justify-center">
        <svg width="1020" height="200" style={{ background: 'transparent' }}>
          <defs>
            {/* Markers for Directed Edges */}
            <marker id="arrow-pending"   viewBox="0 0 10 10" refX="24" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 1 L 10 5 L 0 9 z" fill="#475569" /></marker>
            <marker id="arrow-completed" viewBox="0 0 10 10" refX="24" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 1 L 10 5 L 0 9 z" fill="#10b981" /></marker>
            <marker id="arrow-running"   viewBox="0 0 10 10" refX="24" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 1 L 10 5 L 0 9 z" fill="#3b82f6" /></marker>
            <marker id="arrow-failed"    viewBox="0 0 10 10" refX="24" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 1 L 10 5 L 0 9 z" fill="#ef4444" /></marker>
            <marker id="arrow-retrying"  viewBox="0 0 10 10" refX="24" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 1 L 10 5 L 0 9 z" fill="#f59e0b" /></marker>
          </defs>

          {/* Render Connections */}
          {dagEdges.map((edge, index) => {
            const sourceNode = defaultNodes.find(n => n.id === edge.source);
            const targetNode = defaultNodes.find(n => n.id === edge.target);
            if (!sourceNode || !targetNode) return null;

            // Compute connection state color
            const sourceTask = getTaskForRef(sourceNode.ref);
            const isFailed = sourceTask ? isNodeValidationFailed(sourceTask) : false;
            const sourceStatus = sourceTask ? sourceTask.status : (sourceNode.id === 'upload' ? 'completed' : 'pending');
            const color = getStatusColor(sourceStatus, isFailed);
            const markerId = `arrow-${isFailed ? 'failed' : sourceStatus}`;
            const isActive = sourceStatus === 'running';

            // Control points for nice curves
            let d = `M ${sourceNode.x} ${sourceNode.y} L ${targetNode.x} ${targetNode.y}`;
            if (sourceNode.y !== targetNode.y) {
              const midX = (sourceNode.x + targetNode.x) / 2;
              d = `M ${sourceNode.x} ${sourceNode.y} C ${midX} ${sourceNode.y}, ${midX} ${targetNode.y}, ${targetNode.x} ${targetNode.y}`;
            }

            return (
              <path
                key={index}
                d={d}
                stroke={color}
                strokeWidth={isActive ? "2.5" : "1.5"}
                strokeDasharray={isActive ? "5 3" : "none"}
                fill="none"
                markerEnd={`url(#${markerId})`}
                style={{
                  transition: 'all 0.3s ease',
                  animation: isActive ? 'pulse-dash 1s linear infinite' : 'none'
                }}
              />
            );
          })}

          {/* Render Nodes */}
          {defaultNodes.map((node) => {
            const task = getTaskForRef(node.ref);
            const isFailed = task ? isNodeValidationFailed(task) : false;
            
            let status = task ? task.status : (node.id === 'upload' ? 'completed' : (
              replayMode && replaySnapshots && replayIndex >= 0
                ? (Object.values(replaySnapshots[replayIndex].taskStates).every(t => t.status === 'completed') && Object.keys(replaySnapshots[replayIndex].taskStates).length > 0 ? 'completed' : 'pending')
                : (tasks.every(t => t.status === 'completed') && tasks.length > 0 ? 'completed' : 'pending')
            ));
            
            const isFuture = task && forecastModel?.forecast?.future_tasks?.some(ft => String(ft.task_id) === String(task.id));
            if (isFuture) {
              const ft = forecastModel.forecast.future_tasks.find(ft => String(ft.task_id) === String(task.id));
              if (ft) status = ft.status; 
            }

            const color = getStatusColor(status, isFailed);
            const bg = getStatusBg(status, isFailed);
            
            const isSelected = selectedNodeId === node.id || 
                               (task && selectedNodeId === task.id) ||
                               (task && selectedTaskId === task.id);

            const isBottleneckNode = (() => {
              if (!forecastModel?.forecast?.current_bottleneck) return false;
              const bt = forecastModel.forecast.current_bottleneck.toLowerCase();
              return bt.includes(node.name.toLowerCase()) || bt.includes(node.ref.toLowerCase());
            })();

            const isRemainingCP = task && forecastModel?.forecast?.critical_path?.remaining_tasks?.some(tid => String(tid) === String(task.id));

            // Scheduling Advisor visual overlays
            const hasRec = task && advisorModel?.advisor?.recommendations?.some(r => r.affected_tasks?.some(tid => String(tid) === String(task.id)));
            const cpImprove = task && advisorModel?.advisor?.critical_path_scheduling?.find(cp => String(cp.task_id) === String(task.id) && cp.estimated_gain_ms > 0);
            
            const isQueueBottleneck = (() => {
              if (!task || !task.queue || !advisorModel?.advisor?.queue_analysis?.queues) return false;
              const qStat = advisorModel.advisor.queue_analysis.queues.find(q => q.queue === task.queue);
              return qStat && (qStat.severity === 'high' || qStat.severity === 'medium');
            })();

            const handleNodeClick = () => {
              if (task) {
                const alreadySelected = selectedTaskId === task.id;
                if (alreadySelected) {
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
                  setSelectedWorkerId(task.worker_id || null);
                }
              }
              onSelectNode?.(task || node);
            };

            const diffInfo = getTaskDiffForRef(node.ref);
            const hasDiff = !!diffInfo;

            return (
              <g 
                key={node.id} 
                transform={`translate(${node.x}, ${node.y})`}
                onClick={handleNodeClick}
                style={{ cursor: 'pointer' }}
              >
                <title>{buildTooltipText(node, diffInfo, task)}</title>
                <rect
                  x="-50"
                  y="-22"
                  width="100"
                  height="44"
                  rx="7"
                  fill={bg}
                  stroke={isBottleneckNode ? '#ef4444' : (isRemainingCP ? '#f59e0b' : (isSelected ? '#a78bfa' : color))}
                  strokeWidth={isBottleneckNode ? '4' : (status === 'running' || isSelected || hasDiff || isRemainingCP ? '3' : '1.5')}
                  strokeDasharray={isFuture ? "5 3" : (hasDiff ? "4 2" : "none")}
                  style={{ 
                    transition: 'all 0.2s ease',
                    animation: isBottleneckNode ? 'pulse-bottleneck 1.5s infinite' : 'none'
                  }}
                />
                
                {/* Advisor overlays inside node */}
                {hasRec && (
                  <circle cx="42" cy="-14" r="5" fill="#f59e0b" title="Scheduling Recommendation Available" />
                )}
                {cpImprove && (
                  <circle cx="-42" cy="-14" r="4" fill="#10b981" title={`Critical Path Gain: -${cpImprove.estimated_gain_ms}ms`} />
                )}
                {isQueueBottleneck && (
                  <rect x="-48" y="16" width="96" height="4" fill="#f43f5e" rx="1" title="Congested Queue Bottleneck" />
                )}

                <text
                  x="0"
                  y="-2"
                  textAnchor="middle"
                  fill="#f8fafc"
                  fontSize="9"
                  fontWeight="600"
                  fontFamily="'JetBrains Mono', monospace"
                >
                  {node.name}
                </text>
                {/* Status & Worker */}
                <text
                  x="0"
                  y="12"
                  textAnchor="middle"
                  fill={color}
                  fontSize="8"
                  fontWeight="700"
                  fontFamily="'JetBrains Mono', monospace"
                >
                  {isFailed ? 'VAL FAILED' : (status?.toUpperCase() || 'QUEUED')}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      <style>{`
        @keyframes pulse-dash {
          to { stroke-dashoffset: -10; }
        }
        @keyframes pulse-bottleneck {
          0% { stroke: #ef4444; filter: drop-shadow(0 0 2px rgba(239, 68, 68, 0.4)); }
          50% { stroke: #f87171; filter: drop-shadow(0 0 8px rgba(239, 68, 68, 0.8)); }
          100% { stroke: #ef4444; filter: drop-shadow(0 0 2px rgba(239, 68, 68, 0.4)); }
        }
        .custom-scrollbar::-webkit-scrollbar { height: 6px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: rgba(255, 255, 255, 0.02); }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 3px; }
      `}</style>
    </div>
  );
};

export default PipelineDAG;
