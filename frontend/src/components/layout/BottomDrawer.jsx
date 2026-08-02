import React, { useState, useEffect, useRef } from 'react';

/**
 * Bottom resizable/collapsible Developer Panel framework.
 * Saves height in localStorage to persist user layout preferences.
 */
export const BottomDrawer = ({ 
  isOpen, 
  onClose,
  children 
}) => {
  const [height, setHeight] = useState(() => {
    const saved = localStorage.getItem('scaleflow_drawer_height');
    return saved ? parseInt(saved, 10) : 280;
  });
  const [isResizing, setIsResizing] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    localStorage.setItem('scaleflow_drawer_height', height.toString());
  }, [height]);

  const startResize = (e) => {
    e.preventDefault();
    setIsResizing(true);
  };

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!isResizing) return;
      const newHeight = window.innerHeight - e.clientY;
      // Cap height between 80px and 80% viewport height
      const cappedHeight = Math.min(Math.max(newHeight, 80), window.innerHeight * 0.8);
      setHeight(cappedHeight);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    if (isResizing) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing]);

  if (!isOpen) {
    // Render only the handle/bar collapsed state at bottom
    return (
      <div 
        className="developer-drawer-container collapsed" 
        style={{ height: 'var(--drawer-handle-height)' }}
      >
        <div 
          className="developer-drawer-handle" 
          onClick={onClose} 
          style={{ cursor: 'pointer' }}
          role="button"
          tabIndex={0}
          aria-expanded="false"
          aria-label="Expand Developer Panel"
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClose(); } }}
        >
          <span className="text-label" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>▲</span> Developer Panel (No active pipeline context)
          </span>
        </div>
      </div>
    );
  }

  return (
    <div 
      ref={containerRef}
      className="developer-drawer-container expanded" 
      style={{ height: `${height}px` }}
    >
      <div 
        className="developer-drawer-handle" 
        onMouseDown={startResize}
        role="separator"
        aria-valuenow={height}
        aria-valuemin={80}
        aria-valuemax={window.innerHeight * 0.8}
        aria-label="Resize Developer Panel"
      >
        <span className="text-label" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>▼</span> Developer Panel
        </span>
        <button 
          onClick={onClose}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--text-muted)',
            cursor: 'pointer',
            fontSize: '0.8rem',
            padding: '2px 8px'
          }}
          aria-label="Collapse Developer Panel"
        >
          Collapse
        </button>
      </div>
      <div className="developer-drawer-content">
        {children || (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-12)' }}>
            <h4 className="text-section-title">Explainability Logs</h4>
            <p className="text-caption" style={{ color: 'var(--text-secondary)' }}>
              No document selected. Select a document and run a query to see retrieval, prompt context, and reasoning details here.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default BottomDrawer;
