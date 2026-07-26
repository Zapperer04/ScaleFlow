import React, { useState, useRef, useEffect } from 'react';
import { 
  Send, Sparkles, Copy, FileText, ZoomIn, ZoomOut, 
  ChevronLeft, ChevronRight, BookOpen
} from 'lucide-react';
import Button from '../../ui/Button';

export const ChatWorkspace = ({ 
  chatThread = [], 
  chatQuery = '', 
  onQueryChange, 
  onSubmit, 
  currentQueryStage, 
  queryTimer, 
  activeAnswerDetails, 
  onSuggestedClick,
  pageCount        // real page count from activeDoc?.page_count, or undefined
}) => {
  const messagesEndRef = useRef(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [zoomLevel, setZoomLevel] = useState(100);
  const [highlightedText, setHighlightedText] = useState(null);

  const suggestedQuestions = [
    "Summarise this report",
    "Generate executive summary",
    "Explain page 8",
    "Extract financial metrics",
    "Find all tables",
    "Show key entities"
  ];

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatThread]);

  const handleCopyText = (text) => {
    navigator.clipboard.writeText(text);
  };

  const handleCitationClick = (citation) => {
    const page = citation.page_number || 8;
    setCurrentPage(page);
    setHighlightedText(citation.text);
  };

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'minmax(350px, 1fr) 250px 380px',
        border: '1px solid rgba(255,255,255,0.06)',
        borderRadius: '16px',
        backgroundColor: 'rgba(15, 23, 42, 0.4)',
        backdropFilter: 'blur(20px)',
        height: '520px',
        overflow: 'hidden',
        boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
      }}
    >
      {/* 1. Chat Conversation Column */}
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
        
        {/* Messages List */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }} className="custom-scrollbar">
          
          {/* Active query step progress */}
          {currentQueryStage && currentQueryStage !== 'completed' && (
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '12px', 
              padding: '12px 16px', 
              backgroundColor: 'rgba(59,130,246,0.05)', 
              border: '1px solid rgba(59,130,246,0.15)', 
              borderRadius: '8px', 
              fontSize: '11px', 
              fontFamily: 'monospace' 
            }}>
              <Sparkles size={14} className="animate-pulse text-indigo-400" />
              <div style={{ flex: 1 }}>
                <span>STAGE: <strong>{currentQueryStage.toUpperCase()}</strong></span>
                <span style={{ color: 'var(--text-muted)', marginLeft: '12px' }}>ELAPSED: {queryTimer.toFixed(1)}s</span>
              </div>
            </div>
          )}

          {chatThread.map((msg, idx) => {
            const isUser = msg.role === 'user';
            return (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  justifyContent: isUser ? 'flex-end' : 'flex-start',
                  alignItems: 'flex-start',
                  gap: '12px',
                }}
              >
                {!isUser && (
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '28px', height: '28px', borderRadius: '50%', backgroundColor: 'rgba(59,130,246,0.1)', color: 'var(--color-accent)', flexShrink: 0 }}>
                    <Sparkles size={12} />
                  </div>
                )}
                
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', maxWidth: '80%' }}>
                  <div
                    style={{
                      padding: '12px 16px',
                      borderRadius: '12px',
                      backgroundColor: isUser ? 'var(--color-accent)' : 'rgba(255,255,255,0.02)',
                      border: isUser ? 'none' : '1px solid rgba(255,255,255,0.05)',
                      color: '#fff',
                      fontSize: '0.85rem',
                      lineHeight: '1.5',
                      position: 'relative',
                    }}
                  >
                    {msg.content}
                    
                    {!isUser && (
                      <button
                        onClick={() => handleCopyText(msg.content)}
                        style={{ position: 'absolute', top: '8px', right: '8px', background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '2px' }}
                        title="Copy answer"
                      >
                        <Copy size={12} />
                      </button>
                    )}
                  </div>
                  <span style={{ fontSize: '9px', color: 'var(--text-muted)', alignSelf: isUser ? 'flex-end' : 'flex-start', fontFamily: 'monospace' }}>
                    {msg.timestamp}
                  </span>
                </div>
              </div>
            );
          })}
          <div ref={messagesEndRef} />
        </div>

        {/* Suggested Prompt Cards */}
        {chatThread.length === 1 && (
          <div style={{ padding: '0 24px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <span style={{ fontSize: '9px', fontFamily: 'monospace', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Suggested Questions</span>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              {suggestedQuestions.map((q) => (
                <button
                  key={q}
                  onClick={() => onSuggestedClick(q)}
                  style={{
                    background: 'rgba(255,255,255,0.02)',
                    border: '1px solid rgba(255,255,255,0.06)',
                    borderRadius: '6px',
                    padding: '6px 12px',
                    fontSize: '11px',
                    textAlign: 'left',
                    color: 'var(--text-secondary)',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = 'var(--color-accent)';
                    e.currentTarget.style.color = '#fff';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)';
                    e.currentTarget.style.color = 'var(--text-secondary)';
                  }}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input Bar */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (chatQuery.trim()) onSubmit();
          }}
          style={{
            padding: '16px 24px',
            borderTop: '1px solid rgba(255,255,255,0.05)',
            display: 'flex',
            gap: '12px',
            backgroundColor: 'rgba(0,0,0,0.15)'
          }}
        >
          <input
            type="text"
            placeholder="Ask a question about this document..."
            value={chatQuery}
            onChange={(e) => onQueryChange(e.target.value)}
            disabled={currentQueryStage && currentQueryStage !== 'completed'}
            style={{
              flex: 1,
              backgroundColor: 'rgba(0,0,0,0.2)',
              border: '1px solid rgba(255,255,255,0.06)',
              borderRadius: '8px',
              padding: '0 16px',
              height: '40px',
              color: '#fff',
              outline: 'none',
              fontSize: '0.85rem',
            }}
          />
          <Button
            type="submit"
            variant="primary"
            disabled={!chatQuery.trim() || (currentQueryStage && currentQueryStage !== 'completed')}
            style={{ height: '40px', padding: '0 16px', borderRadius: '8px' }}
          >
            <Send size={15} />
          </Button>
        </form>
      </div>

      {/* 2. Middle Citations / Evidence Inspector Column */}
      <div
        style={{
          borderLeft: '1px solid rgba(255,255,255,0.05)',
          backgroundColor: 'rgba(15, 23, 42, 0.2)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div style={{ padding: '16px', borderBottom: '1px solid rgba(255,255,255,0.05)', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <FileText size={14} style={{ color: 'var(--color-success)' }} />
          <span style={{ fontSize: '10px', fontFamily: 'monospace', fontWeight: 'bold', color: '#fff', textTransform: 'uppercase' }}>Evidence Sources</span>
        </div>
        
        {/* List of citations */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }} className="custom-scrollbar">
          {activeAnswerDetails?.evidence ? activeAnswerDetails.evidence.map((item, idx) => (
            <div
              key={idx}
              onClick={() => handleCitationClick(item)}
              style={{
                backgroundColor: 'rgba(255,255,255,0.02)',
                border: '1px solid rgba(255,255,255,0.06)',
                borderRadius: '8px',
                padding: '12px',
                cursor: 'pointer',
                transition: 'all 0.2s',
                display: 'flex',
                flexDirection: 'column',
                gap: '6px'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = 'rgba(59, 130, 246, 0.4)';
                e.currentTarget.style.background = 'rgba(59, 130, 246, 0.03)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)';
                e.currentTarget.style.background = 'rgba(255,255,255,0.02)';
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--color-success)', fontWeight: 'bold', fontSize: '9px', fontFamily: 'monospace' }}>
                <span>PAGE: {item.page_number || '8'}</span>
                <span>CONF: {(item.score || 0.95).toFixed(2)}</span>
              </div>
              <p style={{ margin: 0, color: 'var(--text-secondary)', lineHeight: '1.4', fontSize: '11px' }}>
                "{item.text.length > 140 ? `${item.text.slice(0, 140)}...` : item.text}"
              </p>
            </div>
          )) : (
            <div style={{ textAlign: 'center', color: 'var(--text-disabled)', padding: '40px 12px', fontSize: '11px' }}>
              Submit a query to inspect citations.
            </div>
          )}
        </div>
      </div>

      {/* 3. Right Integrated Document Preview Panel */}
      <div style={{
        borderLeft: '1px solid rgba(255,255,255,0.05)',
        background: 'rgba(15, 23, 42, 0.4)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden'
      }}>
        {/* Toolbar */}
        <div style={{ 
          padding: '12px 16px', 
          borderBottom: '1px solid rgba(255,255,255,0.05)', 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          background: 'rgba(0,0,0,0.1)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <BookOpen size={14} style={{ color: 'var(--color-accent)' }} />
            <span style={{ fontSize: '10px', fontFamily: 'monospace', fontWeight: 'bold', color: '#fff', textTransform: 'uppercase' }}>Preview</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <button 
              onClick={() => setZoomLevel(prev => Math.max(50, prev - 25))}
              style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
            >
              <ZoomOut size={14} />
            </button>
            <span style={{ fontSize: '10px', fontFamily: 'monospace', color: 'var(--text-secondary)' }}>{zoomLevel}%</span>
            <button 
              onClick={() => setZoomLevel(prev => Math.min(200, prev + 25))}
              style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
            >
              <ZoomIn size={14} />
            </button>
          </div>
        </div>

        {/* Page Sheet Container */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', justifyContent: 'center', alignItems: 'flex-start' }} className="custom-scrollbar">
          <div style={{
            width: '100%',
            maxWidth: '320px',
            background: '#fff',
            color: '#1e293b',
            borderRadius: '4px',
            padding: '24px',
            boxShadow: '0 4px 20px rgba(0,0,0,0.4)',
            fontSize: '11px',
            lineHeight: '1.6',
            transform: `scale(${zoomLevel / 100})`,
            transformOrigin: 'top center',
            transition: 'transform 0.2s',
            minHeight: '400px',
            position: 'relative'
          }}>
            {/* Page number banner — pageCount comes from activeDoc.page_count */}
            <div style={{ position: 'absolute', top: '8px', right: '12px', fontSize: '9px', color: '#94a3b8', fontWeight: 600 }}>
              Page {currentPage}{pageCount ? ` of ${pageCount}` : ''}
            </div>

            {/* Bounding box highlight overlay */}
            {highlightedText && (
              <div style={{
                position: 'absolute',
                top: '60px',
                left: '20px',
                right: '20px',
                background: 'rgba(59, 130, 246, 0.15)',
                border: '1.5px solid rgba(59, 130, 246, 0.6)',
                borderRadius: '3px',
                padding: '6px',
                color: '#1e3a8a',
                fontWeight: 500,
                fontSize: '10px',
                boxShadow: '0 0 10px rgba(59, 130, 246, 0.2)'
              }}>
                <span style={{ display: 'block', fontSize: '8px', textTransform: 'uppercase', color: '#3b82f6', fontWeight: 700, marginBottom: '2px' }}>Cited Passage Highlight</span>
                "{highlightedText}"
              </div>
            )}

            {/* Document preview — rendered pages will appear here when citation is clicked.
                The mock document body has been removed. This panel shows cited passage highlights.
                A full PDF renderer (pdfjs-dist) is available in the Document Viewer tab. */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '280px', color: '#94a3b8', gap: '8px', marginTop: highlightedText ? '90px' : '0', transition: 'margin-top 0.2s' }}>
              <BookOpen size={28} style={{ opacity: 0.3 }} />
              <span style={{ fontSize: '11px', textAlign: 'center', opacity: 0.5 }}>
                Click a citation to highlight the source passage
              </span>
            </div>
          </div>
        </div>

        {/* Page Nav Footer */}
        <div style={{ 
          padding: '12px 16px', 
          borderTop: '1px solid rgba(255,255,255,0.05)', 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          background: 'rgba(0,0,0,0.1)'
        }}>
          <button 
            disabled={currentPage <= 1}
            onClick={() => {
              setCurrentPage(prev => Math.max(1, prev - 1));
              setHighlightedText(null);
            }}
            style={{ background: 'none', border: 'none', color: currentPage <= 1 ? 'var(--text-disabled)' : 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}
          >
            <ChevronLeft size={16} /> Prev
          </button>
          <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
            Page {currentPage}{pageCount ? ` / ${pageCount}` : ''}
          </span>
          <button 
            disabled={pageCount ? currentPage >= pageCount : false}
            onClick={() => {
              setCurrentPage(prev => pageCount ? Math.min(pageCount, prev + 1) : prev + 1);
              setHighlightedText(null);
            }}
            style={{ background: 'none', border: 'none', color: (pageCount && currentPage >= pageCount) ? 'var(--text-disabled)' : 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}
          >
            Next <ChevronRight size={16} />
          </button>
        </div>
      </div>

      <style>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 5px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(255,255,255,0.08);
          border-radius: 3px;
        }
      `}</style>
    </div>
  );
};

export default ChatWorkspace;
