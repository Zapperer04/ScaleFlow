import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom';
import SearchInput from './SearchInput';
import useFocusTrap from '../../hooks/useFocusTrap';
import useEscapeKey from '../../hooks/useEscapeKey';

/**
 * Reusable Command Palette overlay component.
 */
export const CommandPalette = ({
  isOpen,
  onClose,
  actions = []
}) => {
  const [search, setSearch] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const containerRef = useFocusTrap(isOpen);
  useEscapeKey(onClose, isOpen);

  // Filter actions based on query
  const filteredActions = actions.filter(action =>
    action.label.toLowerCase().includes(search.toLowerCase()) ||
    action.category.toLowerCase().includes(search.toLowerCase())
  );

  // Reset active index when search query updates
  useEffect(() => {
    setActiveIndex(0);
  }, [search]);

  // Keyboard navigation listeners
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setActiveIndex(prev => (prev + 1) % Math.max(1, filteredActions.length));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setActiveIndex(prev => (prev - 1 + filteredActions.length) % Math.max(1, filteredActions.length));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (filteredActions[activeIndex]) {
          filteredActions[activeIndex].perform();
          onClose();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, filteredActions, activeIndex, onClose]);

  // Prevent scroll when palette is active
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return ReactDOM.createPortal(
    <div className="modal-overlay-backdrop command-palette-backdrop" onClick={onClose} style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0, 0, 0, 0.65)', backdropFilter: 'blur(4px)', display: 'flex', justifyContent: 'center', paddingTop: '15vh', zIndex: 'var(--z-index-overlay)' }}>
      <div
        className="command-palette-card panel"
        onClick={e => e.stopPropagation()}
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-label="Command Palette"
        style={{
          width: '90%',
          maxWidth: '600px',
          maxHeight: '50vh',
          display: 'flex',
          flexDirection: 'column',
          padding: 'var(--spacing-16)',
          background: 'var(--bg-panel)',
          borderColor: 'var(--border-subtle)',
          borderRadius: 'var(--radius-8)',
          boxShadow: 'var(--shadow-large)'
        }}
      >
        <SearchInput
          placeholder="Type a command or navigate..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          autoFocus
        />

        <div className="command-palette-results" style={{ marginTop: 'var(--spacing-12)', overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {filteredActions.length > 0 ? (
            filteredActions.map((action, idx) => {
              const isActive = idx === activeIndex;
              return (
                <div
                  key={action.id}
                  onClick={() => {
                    action.perform();
                    onClose();
                  }}
                  style={{
                    padding: 'var(--spacing-12)',
                    borderRadius: 'var(--radius-4)',
                    background: isActive ? 'var(--bg-hover)' : 'transparent',
                    borderLeft: isActive ? '3px solid var(--color-accent)' : '3px solid transparent',
                    cursor: 'pointer',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    transition: 'var(--transition-fast-ease)'
                  }}
                >
                  <div>
                    <span className="text-body" style={{ color: 'var(--text-primary)', fontWeight: 'var(--font-weight-medium)' }}>
                      {action.label}
                    </span>
                    <span className="text-caption" style={{ display: 'block', color: 'var(--text-disabled)' }}>
                      {action.category}
                    </span>
                  </div>
                  {isActive && (
                    <span className="text-caption" style={{ color: 'var(--color-accent)' }}>
                      Enter ↵
                    </span>
                  )}
                </div>
              );
            })
          ) : (
            <div className="text-body" style={{ padding: 'var(--spacing-20)', textAlign: 'center', color: 'var(--text-disabled)' }}>
              No commands matched your query.
            </div>
          )}
        </div>
        
        <div className="command-palette-footer text-caption" style={{ borderTop: '1px solid var(--border-divider)', paddingTop: 'var(--spacing-12)', marginTop: 'var(--spacing-12)', display: 'flex', justifyContent: 'space-between', color: 'var(--text-disabled)' }}>
          <span>↑↓ Arrow keys to navigate</span>
          <span>↵ Enter to select</span>
          <span>esc to close</span>
        </div>
      </div>
    </div>,
    document.body
  );
};
export default CommandPalette;
