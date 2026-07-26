import React from 'react';

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
export const PipelineDAG = ({ tasks = [], dagNodes = [], dagEdges = [], onSelectNode, selectedNodeId }) => {
  // Frozen MR-RAG Pipeline layout nodes if backend nodes are not pre-positioned
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

  // Helper to resolve task state by matching task_type
  const getTaskForRef = (refName) => {
    return tasks.find(t => t.type === refName || t.task_type === refName) || null;
  };

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'completed': return '#10b981';
      case 'running': return '#3b82f6';
      case 'failed': return '#ef4444';
      case 'paused':
      case 'retrying': return '#f59e0b';
      case 'pending':
      case 'queued': return '#64748b';
      default: return '#64748b';
    }
  };

  const getStatusBg = (status) => {
    switch (status?.toLowerCase()) {
      case 'completed': return 'rgba(16, 185, 129, 0.08)';
      case 'running': return 'rgba(59, 130, 246, 0.08)';
      case 'failed': return 'rgba(239, 68, 68, 0.08)';
      case 'paused':
      case 'retrying': return 'rgba(245, 158, 11, 0.08)';
      default: return 'rgba(255, 255, 255, 0.02)';
    }
  };

  // Connections for frozen pipeline flow
  const connections = [
    { from: 'upload', to: 'preprocess' },
    { from: 'preprocess', to: 'parse' },
    { from: 'parse', to: 'graph' },
    { from: 'parse', to: 'chunk' },
    { from: 'graph', to: 'embedding' },
    { from: 'chunk', to: 'embedding' },
    { from: 'embedding', to: 'bm25' },
    { from: 'bm25', to: 'retrieval' },
    { from: 'retrieval', to: 'ready' }
  ];

  return (
    <div
      style={{
        backgroundColor: 'rgba(0,0,0,0.2)',
        border: '1px solid rgba(255,255,255,0.06)',
        borderRadius: '12px',
        padding: '16px',
        position: 'relative',
        overflowX: 'auto',
        width: '100%'
      }}
      className="custom-scrollbar"
    >
      <svg viewBox="0 0 1020 200" style={{ width: '100%', minWidth: '940px', height: '200px' }}>
        {/* Render Connection Lines */}
        {connections.map((c, i) => {
          const fromNode = defaultNodes.find(n => n.id === c.from);
          const toNode = defaultNodes.find(n => n.id === c.to);
          const fromTask = getTaskForRef(fromNode.ref);
          const toTask = getTaskForRef(toNode.ref);

          const fromStatus = fromTask ? fromTask.status : (c.from === 'upload' || c.from === 'ready' ? 'completed' : 'pending');
          const toStatus = toTask ? toTask.status : 'pending';

          const isActive = fromStatus === 'completed' && toStatus === 'running';
          const isDone = fromStatus === 'completed' && toStatus === 'completed';

          let strokeColor = '#334155';
          let strokeWidth = '1.5';
          let dashArray = '4 4';

          if (isDone) {
            strokeColor = '#10b981';
            strokeWidth = '2';
            dashArray = 'none';
          } else if (isActive) {
            strokeColor = '#3b82f6';
            strokeWidth = '2.5';
            dashArray = '6 4';
          }

          return (
            <path
              key={i}
              d={`M ${fromNode.x + 50} ${fromNode.y} L ${toNode.x - 50} ${toNode.y}`}
              stroke={strokeColor}
              strokeWidth={strokeWidth}
              strokeDasharray={dashArray}
              fill="none"
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
          const status = task ? task.status : (node.id === 'upload' ? 'completed' : (tasks.every(t => t.status === 'completed') && tasks.length > 0 ? 'completed' : 'pending'));
          const color = getStatusColor(status);
          const bg = getStatusBg(status);
          const isSelected = selectedNodeId === node.id || (task && selectedNodeId === task.id);

          return (
            <g 
              key={node.id} 
              transform={`translate(${node.x}, ${node.y})`}
              onClick={() => onSelectNode?.(task || node)}
              style={{ cursor: 'pointer' }}
            >
              {/* Outer boundary box */}
              <rect
                x="-50"
                y="-22"
                width="100"
                height="44"
                rx="7"
                fill={bg}
                stroke={isSelected ? '#a78bfa' : color}
                strokeWidth={status === 'running' || isSelected ? '2.5' : '1.5'}
                style={{ transition: 'all 0.2s ease' }}
              />
              {/* Text label */}
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
                {status?.toUpperCase() || 'QUEUED'}
              </text>
            </g>
          );
        })}
      </svg>

      <style>{`
        @keyframes pulse-dash {
          to { stroke-dashoffset: -10; }
        }
        .custom-scrollbar::-webkit-scrollbar { height: 6px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: rgba(255, 255, 255, 0.02); }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 3px; }
      `}</style>
    </div>
  );
};

export default PipelineDAG;
