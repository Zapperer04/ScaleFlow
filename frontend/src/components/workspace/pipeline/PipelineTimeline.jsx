import React from 'react';
import PipelineStage from './PipelineStage';


export const PipelineTimeline = ({ stages = [] }) => {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 0,
        padding: '8px 0',
        width: '100%',
      }}
    >
      {/* Horizontal scroll wrapper for wide pipelines */}
      <div style={{
        display: 'flex',
        flexDirection: 'row',
        alignItems: 'center',
        gap: 0,
        overflowX: 'auto',
        width: '100%',
        padding: '12px 4px',
      }} className="pipeline-scroll">
        {stages.map((stage, index) => {
          const statusKey = stage.status?.toLowerCase() || 'waiting';
          const isActive  = statusKey === 'running';
          const isDone    = statusKey === 'completed';
          return (
            <React.Fragment key={stage.name}>
              <PipelineStage
                name={stage.name}
                status={stage.status}
                durationSeconds={stage.durationSeconds}
                retriesCount={stage.retriesCount}
              />
              {index < stages.length - 1 && (
                <div style={{ display: 'flex', alignItems: 'center', flexShrink: 0, padding: '0 6px' }}>
                  {/* Horizontal connector between stages */}
                  <div style={{ position: 'relative', width: 32, height: 2, backgroundColor: 'rgba(255,255,255,0.06)', borderRadius: 2, overflow: 'hidden' }}>
                    {isDone && (
                      <div style={{ position: 'absolute', inset: 0, backgroundColor: '#10b981', borderRadius: 2 }} />
                    )}
                    {isActive && (
                      <div style={{
                        position: 'absolute',
                        top: 0,
                        bottom: 0,
                        left: 0,
                        width: '50%',
                        background: 'linear-gradient(to right, #3b82f6, transparent)',
                        animation: 'flowRight 0.8s linear infinite',
                      }} />
                    )}
                  </div>
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>

      <style>{`
        @keyframes flowRight {
          from { left: -50%; }
          to   { left: 100%; }
        }
        .pipeline-scroll::-webkit-scrollbar { height: 4px; }
        .pipeline-scroll::-webkit-scrollbar-track { background: rgba(255,255,255,0.02); border-radius: 2px; }
        .pipeline-scroll::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 2px; }
      `}</style>
    </div>
  );
};

export default PipelineTimeline;
