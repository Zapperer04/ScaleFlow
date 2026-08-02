import React, { useEffect, useRef } from 'react';
import { usePipeline } from '../../../contexts/PipelineContext';
import { FileText, Eye } from 'lucide-react';

export const DocumentViewer = () => {
  const { queryResult, selectedCitation, selectedChunk, selectedGraphNode } = usePipeline();
  const containerRef = useRef(null);

  // Determine active item to highlight
  const activeItem = selectedCitation || selectedChunk || 
    (selectedGraphNode ? (queryResult?.context?.sections || []).find(s => s.chunk_id === selectedGraphNode || s.section_id === selectedGraphNode) : null);

  const activePage = activeItem?.page || 1;
  const bbox = activeItem?.bbox;

  // Scroll active item into view when it changes
  useEffect(() => {
    if (activeItem && containerRef.current) {
      const pageEl = containerRef.current.querySelector(`#document-page-${activePage}`);
      if (pageEl) {
        pageEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }, [activeItem, activePage]);

  // Extract all pages from context to simulate
  const pagesList = Array.from(new Set([
    ...(queryResult?.context?.sections || []).map(s => s.page),
    ...(queryResult?.context?.tables || []).map(t => t.page),
    ...(queryResult?.context?.figures || []).map(f => f.page),
    ...(queryResult?.context?.supporting_chunks || []).map(sc => sc.page)
  ].filter(p => p !== undefined && p !== null))).sort((a, b) => a - b);

  if (pagesList.length === 0) {
    pagesList.push(1);
  }

  return (
    <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '20px', display: 'flex', flexDirection: 'column', height: '100%', minHeight: '400px' }}>
      <h3 style={{ margin: '0 0 16px 0', fontSize: '0.9rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <Eye size={16} />
        Canonical Document Viewer
      </h3>

      <div style={{ display: 'flex', gap: '16px', flex: 1, minHeight: 0 }}>
        {/* Thumbnails Sidebar */}
        <div style={{ width: '80px', borderRight: '1px solid var(--border-subtle)', paddingRight: '12px', display: 'flex', flexDirection: 'column', gap: '10px', overflowY: 'auto' }}>
          {pagesList.map(page => (
            <div
              key={page}
              onClick={() => {
                const pageEl = containerRef.current.querySelector(`#document-page-${page}`);
                if (pageEl) {
                  pageEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
              }}
              style={{
                width: '60px',
                height: '80px',
                background: activePage === page ? 'rgba(139, 92, 246, 0.15)' : 'var(--bg-primary)',
                border: activePage === page ? '2px solid var(--color-accent)' : '1px solid var(--border-subtle)',
                borderRadius: '4px',
                cursor: 'pointer',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '4px',
                transition: 'all 0.2s ease'
              }}
            >
              <FileText size={16} style={{ color: activePage === page ? 'var(--color-accent)' : 'var(--text-muted)' }} />
              <span style={{ fontSize: '0.65rem', fontWeight: 'bold', color: 'var(--text-primary)' }}>P. {page}</span>
            </div>
          ))}
        </div>

        {/* Main PDF Rendering viewport */}
        <div ref={containerRef} style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '20px', padding: '10px', background: 'var(--bg-primary)', borderRadius: '6px', border: '1px solid var(--border-subtle)' }}>
          {pagesList.map(page => {
            // Find text blocks belonging to this page
            const pageBlocks = [
              ...(queryResult?.context?.sections || []).filter(s => s.page === page),
              ...(queryResult?.context?.tables || []).filter(t => t.page === page),
              ...(queryResult?.context?.figures || []).filter(f => f.page === page),
              ...(queryResult?.context?.supporting_chunks || []).filter(sc => sc.page === page)
            ];

            return (
              <div
                key={page}
                id={`document-page-${page}`}
                style={{
                  minHeight: '400px',
                  background: 'var(--bg-panel)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '6px',
                  padding: '24px',
                  position: 'relative',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px'
                }}
              >
                <div style={{ position: 'absolute', top: '8px', right: '12px', fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 'bold' }}>
                  Page {page}
                </div>

                {/* Render spatial bounding box highlight if matching active page */}
                {activePage === page && bbox && (
                  <div
                    style={{
                      position: 'absolute',
                      top: `${(bbox.ymin ?? bbox.y1 ?? 0) * 100}%`,
                      left: `${(bbox.xmin ?? bbox.x1 ?? 0) * 100}%`,
                      width: `${((bbox.xmax ?? bbox.x2 ?? 1) - (bbox.xmin ?? bbox.x1 ?? 0)) * 100}%`,
                      height: `${((bbox.ymax ?? bbox.y2 ?? 1) - (bbox.ymin ?? bbox.y1 ?? 0)) * 100}%`,
                      border: '3px solid var(--color-success)',
                      background: 'rgba(16, 185, 129, 0.12)',
                      pointerEvents: 'none',
                      zIndex: 10,
                      borderRadius: '4px',
                      boxShadow: '0 0 10px var(--color-success)',
                      transition: 'all 0.3s ease'
                    }}
                  />
                )}

                {/* Render Page Content */}
                {pageBlocks.length === 0 ? (
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', textAlign: 'center', marginTop: '100px' }}>
                    [Simulated Page Layout Nodes]
                  </div>
                ) : (
                  pageBlocks.map((blk, bIdx) => (
                    <div
                      key={bIdx}
                      style={{
                        padding: '10px',
                        background: 'var(--bg-primary)',
                        borderRadius: '4px',
                        border: '1px solid var(--border-subtle)',
                        fontSize: '0.8rem',
                        lineHeight: 1.5,
                        color: 'var(--text-primary)'
                      }}
                    >
                      {blk.text}
                    </div>
                  ))
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
export default DocumentViewer;
