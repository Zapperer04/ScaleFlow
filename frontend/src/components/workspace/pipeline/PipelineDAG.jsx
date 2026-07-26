import React from 'react';

export const PipelineDAG = ({ stages = [] }) => {
  // Helper to lookup stage status
  const getStageStatus = (name) => {
    const matched = stages.find(s => s.name?.toLowerCase().includes(name.toLowerCase()));
    return matched ? matched.status : 'waiting';
  };

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'completed': return 'var(--color-success)';
      case 'running': return 'var(--color-accent)';
      case 'failed': return 'var(--color-failure)';
      case 'paused': return 'var(--color-warning)';
      default: return 'var(--border-subtle)';
    }
  };

  const getStatusBg = (status) => {
    switch (status?.toLowerCase()) {
      case 'completed': return 'rgba(16, 185, 129, 0.05)';
      case 'running': return 'rgba(79, 70, 229, 0.05)';
      case 'failed': return 'rgba(244, 63, 94, 0.05)';
      case 'paused': return 'rgba(245, 158, 11, 0.05)';
      default: return 'rgba(255, 255, 255, 0.01)';
    }
  };

  const nodes = [
    { id: 'pdf', name: 'PDF Ingestion', x: 40, y: 100, ref: 'Upload' },
    { id: 'ocr', name: 'OCR Engine', x: 140, y: 100, ref: 'OCR' },
    { id: 'layout', name: 'Layout Analysis', x: 240, y: 100, ref: 'Vision' },
    { id: 'tables', name: 'Table Detector', x: 370, y: 40, ref: 'Layout' },
    { id: 'images', name: 'Image Extractor', x: 370, y: 160, ref: 'Layout' },
    { id: 'chunks', name: 'Chunk Builder', x: 500, y: 100, ref: 'Chunk' },
    { id: 'entities', name: 'Entity Extractor', x: 630, y: 40, ref: 'Knowledge' },
    { id: 'graph', name: 'Graph Builder', x: 630, y: 160, ref: 'Graph' },
    { id: 'hybrid', name: 'Hybrid Indexer', x: 760, y: 100, ref: 'Hybrid' },
    { id: 'validation', name: 'Validation', x: 860, y: 100, ref: 'Validation' },
    { id: 'ready', name: 'Ready State', x: 940, y: 100, ref: 'Ready' }
  ];

  const connections = [
    { from: 'pdf', to: 'ocr' },
    { from: 'ocr', to: 'layout' },
    { from: 'layout', to: 'tables' },
    { from: 'layout', to: 'images' },
    { from: 'tables', to: 'chunks' },
    { from: 'images', to: 'chunks' },
    { from: 'chunks', to: 'entities' },
    { from: 'chunks', to: 'graph' },
    { from: 'entities', to: 'hybrid' },
    { from: 'graph', to: 'hybrid' },
    { from: 'hybrid', to: 'validation' },
    { from: 'validation', to: 'ready' }
  ];

  return (
    <div
      style={{
        backgroundColor: 'rgba(0,0,0,0.15)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-10)',
        padding: 'var(--spacing-16)',
        position: 'relative',
        overflowX: 'auto',
        width: '100%'
      }}
      className="custom-scrollbar"
    >
      <svg viewBox="0 0 1020 200" style={{ width: '100%', minWidth: '920px', height: '200px' }}>
        
        {/* Render Connection Lines */}
        {connections.map((c, i) => {
          const fromNode = nodes.find(n => n.id === c.from);
          const toNode = nodes.find(n => n.id === c.to);
          const fromStatus = getStageStatus(fromNode.ref);
          const toStatus = getStageStatus(toNode.ref);
          
          const isActive = fromStatus === 'completed' && toStatus === 'running';
          const isDone = fromStatus === 'completed' && toStatus === 'completed';
          
          let strokeColor = 'var(--border-subtle)';
          let strokeWidth = '1';
          let dashArray = '3 3';
          
          if (isDone) {
            strokeColor = 'var(--color-success)';
            strokeWidth = '1.5';
            dashArray = 'none';
          } else if (isActive) {
            strokeColor = 'var(--color-accent)';
            strokeWidth = '2';
            dashArray = '5 5';
          }

          return (
            <path
              key={i}
              d={`M ${fromNode.x + 45} ${fromNode.y} L ${toNode.x - 45} ${toNode.y}`}
              stroke={strokeColor}
              strokeWidth={strokeWidth}
              strokeDasharray={dashArray}
              fill="none"
              style={{
                transition: 'stroke 0.2s, stroke-width 0.2s',
                animation: isActive ? 'pulse-dash 1s linear infinite' : 'none'
              }}
            />
          );
        })}

        {/* Render Nodes */}
        {nodes.map((node) => {
          const status = getStageStatus(node.ref);
          const color = getStatusColor(status);
          const bg = getStatusBg(status);

          return (
            <g key={node.id} transform={`translate(${node.x}, ${node.y})`}>
              {/* Outer boundary box */}
              <rect
                x="-45"
                y="-20"
                width="90"
                height="40"
                rx="6"
                fill={bg}
                stroke={color}
                strokeWidth={status === 'running' ? '2' : '1'}
                style={{ transition: 'stroke 0.2s, fill 0.2s' }}
              />
              {/* Text label */}
              <text
                x="0"
                y="2"
                textAnchor="middle"
                fill="var(--text-primary)"
                fontSize="8.5"
                fontWeight="600"
                fontFamily="var(--font-mono)"
              >
                {node.name}
              </text>
              <text
                x="0"
                y="12"
                textAnchor="middle"
                fill={color}
                fontSize="7.5"
                fontWeight="bold"
                fontFamily="var(--font-mono)"
              >
                {status.toUpperCase()}
              </text>
            </g>
          );
        })}
      </svg>
      
      <style>{`
        @keyframes pulse-dash {
          to {
            stroke-dashoffset: -10;
          }
        }
        .custom-scrollbar::-webkit-scrollbar {
          height: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: rgba(255, 255, 255, 0.02);
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: var(--border-subtle);
          border-radius: 3px;
        }
      `}</style>
    </div>
  );
};
export default PipelineDAG;
