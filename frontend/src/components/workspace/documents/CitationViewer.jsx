import React from 'react';
import { usePipeline } from '../../../contexts/PipelineContext';
import { Bookmark, MapPin, AlignLeft } from 'lucide-react';

export const CitationViewer = () => {
  const { queryResult, selectedCitation, selectCitation } = usePipeline();
  const citations = queryResult?.citations || [];

  return (
    <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '20px', display: 'flex', flexDirection: 'column', height: '100%', minHeight: '400px' }}>
      <h3 style={{ margin: '0 0 16px 0', fontSize: '0.9rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <Bookmark size={16} />
        Grounded Citations Viewer
      </h3>

      {citations.length === 0 ? (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          No citations resolved. Run a query in the Query Workbench to populate.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', overflowY: 'auto', flex: 1 }}>
          {citations.map((cit, idx) => {
            const isSelected = selectedCitation?.citation_id === cit.citation_id;
            const bbox = cit.bbox;
            const formattedBbox = bbox ? `[ymin: ${bbox.ymin?.toFixed(2)}, xmin: ${bbox.xmin?.toFixed(2)}, ymax: ${bbox.ymax?.toFixed(2)}, xmax: ${bbox.xmax?.toFixed(2)}]` : 'N/A';

            return (
              <div
                key={idx}
                onClick={() => selectCitation(cit)}
                style={{
                  background: isSelected ? 'rgba(16, 185, 129, 0.12)' : 'var(--bg-primary)',
                  border: isSelected ? '2px solid var(--color-success)' : '1px solid var(--border-subtle)',
                  borderRadius: '6px',
                  padding: '14px',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--color-success)' }}>
                    Citation {cit.citation_id}
                  </span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                    <MapPin size={12} />
                    Page {cit.page}
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                  <AlignLeft size={12} />
                  <span>Section: {cit.section}</span>
                </div>

                <div style={{ background: 'var(--bg-panel)', padding: '8px', borderRadius: '4px', borderLeft: '3px solid var(--color-success)', fontSize: '0.75rem', fontStyle: 'italic', color: 'var(--text-primary)' }}>
                  "{cit.snippet}"
                </div>

                <div style={{ fontSize: '0.65rem', color: 'var(--text-disabled)', fontFamily: 'monospace' }}>
                  Coordinates: {formattedBbox}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
export default CitationViewer;
