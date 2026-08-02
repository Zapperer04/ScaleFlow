import React from 'react';
import { usePipeline } from '../../../contexts/PipelineContext';
import { Compass, FileText, Database, Image as ImageIcon } from 'lucide-react';

export const GraphExplorer = () => {
  const { queryResult, selectedGraphNode, selectGraphNode } = usePipeline();

  const nodes = queryResult?.context?.sections || [];
  const tables = queryResult?.context?.tables || [];
  const figures = queryResult?.context?.figures || [];
  const graphEvidence = queryResult?.context?.graph_evidence || [];

  // Group all unique graph elements
  const allNodes = [
    ...nodes.map(n => ({ ...n, type: 'section', label: `Sec: ${n.section_id || n.chunk_id}` })),
    ...tables.map(t => ({ ...t, type: 'table', label: `Table: ${t.chunk_id}` })),
    ...figures.map(f => ({ ...f, type: 'figure', label: `Figure: ${f.chunk_id}` })),
    ...graphEvidence.map(g => ({ ...g, type: g.type || 'graph_evidence', label: g.id || `Node: ${g.chunk_id}` }))
  ];

  const handleNodeClick = (id) => {
    selectGraphNode(id);
  };

  return (
    <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '20px', display: 'flex', flexDirection: 'column', height: '100%', minHeight: '400px' }}>
      <h3 style={{ margin: '0 0 16px 0', fontSize: '0.9rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <Compass size={16} />
        Interactive Document Graph Explorer
      </h3>
      
      {allNodes.length === 0 ? (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          No graph data available. Run a query in the Query Workbench to populate.
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px', overflowY: 'auto', flex: 1 }}>
          {allNodes.map((node, idx) => {
            const isSelected = selectedGraphNode === node.chunk_id || selectedGraphNode === node.id || selectedGraphNode === node.section_id;
            const isTable = node.type === 'table';
            const isFigure = node.type === 'figure';
            
            return (
              <div
                key={idx}
                onClick={() => handleNodeClick(node.chunk_id || node.id || node.section_id)}
                style={{
                  background: isSelected ? 'rgba(139, 92, 246, 0.15)' : 'var(--bg-primary)',
                  border: isSelected ? '2px solid var(--color-accent)' : '1px solid var(--border-subtle)',
                  borderRadius: '8px',
                  padding: '16px',
                  cursor: 'pointer',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                  transition: 'all 0.2s ease',
                  position: 'relative'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {isTable ? (
                    <Database size={16} style={{ color: '#3b82f6' }} />
                  ) : isFigure ? (
                    <ImageIcon size={16} style={{ color: '#ec4899' }} />
                  ) : (
                    <FileText size={16} style={{ color: '#10b981' }} />
                  )}
                  <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {node.label}
                  </span>
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                  {node.text}
                </div>
                {node.page && (
                  <div style={{ fontSize: '0.65rem', color: 'var(--color-accent)', fontWeight: 'bold', marginTop: 'auto' }}>
                    Page {node.page}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
export default GraphExplorer;
