import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Send, Sparkles, Copy,
  StopCircle,
  ZoomIn, ZoomOut, ChevronLeft, ChevronRight,
  BookOpen, Search, FileText, UploadCloud, Trash2,
  Loader2, AlertCircle, RotateCw, Maximize2
} from 'lucide-react';
import Button from '../../ui/Button';
import FormattedMessage from '../../ui/FormattedMessage';

/**
 * WORKSPACE_READY — AI Chat Workspace
 *
 * Rendered ONLY after pipeline status === 'completed'.
 * Two-column layout: 40% PDF Viewer | 60% AI Chat
 *
 * Features:
 * - Streaming chat with token-by-token display
 * - Suggested follow-up questions
 * - Citation chips → PDF highlight sync
 * - Conversation history
 * - Copy / Regenerate / Stop actions
 *
 * All developer tools (Retrieval, Graph, Telemetry) remain
 * exclusively in the bottom Developer Panel.
 */
export const ReadyWorkspace = ({
  /** Active document object */
  activeDoc,
  uploadedFiles = [],
  selectedDocumentId,
  onSelectDocument,
  /** Pipeline artifacts (for stats) */
  activeDag,
  pipelineMetadata,
  /** Chat thread array: [{ role, content, timestamp, citations?, isStreaming? }] */
  chatThread = [],
  chatQuery = '',
  onQueryChange,
  onSubmit,
  currentQueryStage,
  queryTimer,
  activeAnswerDetails,
  /** Callback to stop streaming */
  onStopGeneration,
  /** Callback when citation chip is clicked */
  onCitationClick,
  /** pdfjs document object */
  pdfDoc,
  pdfLoading = false,
  pdfError = null,
  pdfTextContent = null,
  pdfNumPages = 1,
  onRetryLoadPdf,
  activePdfPage,
  setActivePdfPage,
  zoomLevel,
  setZoomLevel,
  canvasRef,
  highlights = [],
  /** Callback: user wants to reupload a new document */
  onReupload,
  onDelete,
}) => {
  const messagesEndRef = useRef(null);
  const pdfContainerRef = useRef(null);
  const containerGridRef = useRef(null);
  const [pdfSearchQuery, setPdfSearchQuery] = useState('');

  // ── LeetCode-style panel resizer state ────────────────────
  const [splitWidth, setSplitWidth] = useState(45);
  const [isResizing, setIsResizing] = useState(false);

  const startResizing = useCallback((e) => {
    e.preventDefault();
    setIsResizing(true);
  }, []);

  useEffect(() => {
    if (!isResizing) return;

    const handleMouseMove = (e) => {
      if (!containerGridRef.current) return;
      const rect = containerGridRef.current.getBoundingClientRect();
      const relativeX = e.clientX - rect.left;
      const newWidthPercent = Math.min(80, Math.max(20, (relativeX / rect.width) * 100));
      setSplitWidth(newWidthPercent);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing]);

  // Auto-fit PDF page to container width
  const handleFitToWidth = useCallback(() => {
    if (!pdfContainerRef.current || !pdfDoc) return;
    pdfDoc.getPage(activePdfPage).then((page) => {
      const containerWidth = pdfContainerRef.current.clientWidth - 40;
      if (containerWidth <= 0) return;
      const unscaledViewport = page.getViewport({ scale: 1.0 });
      const fitZoom = Math.min(250, Math.max(50, Math.round((containerWidth / unscaledViewport.width) * 100)));
      setZoomLevel(fitZoom);
    }).catch(() => {});
  }, [pdfDoc, activePdfPage, setZoomLevel]);

  // Auto-fit document width when pdfDoc loads or splitWidth resizes
  useEffect(() => {
    if (pdfDoc) {
      handleFitToWidth();
    }
  }, [pdfDoc, splitWidth, handleFitToWidth]);

  // Trackpad pinch-to-zoom (palm gesture) and Cmd/Ctrl wheel zoom handler
  useEffect(() => {
    const container = pdfContainerRef.current;
    if (!container) return;

    const handleWheel = (e) => {
      if (e.ctrlKey || e.metaKey) {
        e.preventDefault();
        const delta = e.deltaY;
        setZoomLevel((prev) => {
          const change = delta > 0 ? -8 : 8;
          return Math.min(250, Math.max(40, prev + change));
        });
      }
    };

    container.addEventListener('wheel', handleWheel, { passive: false });
    return () => {
      container.removeEventListener('wheel', handleWheel);
    };
  }, [setZoomLevel]);

  // Auto-scroll chat to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatThread]);

  // Filter only PROCESSED / COMPLETED documents for AI Chat selector
  const processedDocs = (uploadedFiles || []).filter((f) => {
    const s = (f.status || '').toLowerCase();
    return s === 'completed' || s === 'processed';
  });

  const pageCount = activeDoc?.page_count || pipelineMetadata?.summary?.pages || pdfNumPages || pdfDoc?.numPages || 1;
  const chunkCount =
    pipelineMetadata?.chunk_count ||
    (activeDag?.artifacts || []).find((a) => a.artifact_type === 'graph_chunks')
      ?.metadata_json?.chunk_count;
  const processingTime = (() => {
    const pipeline = activeDag?.pipeline;
    if (!pipeline?.started_at || !pipeline?.completed_at) return null;
    const secs = Math.round(
      (new Date(pipeline.completed_at) - new Date(pipeline.started_at)) / 1000
    );
    return secs >= 60
      ? `${Math.floor(secs / 60)}m ${secs % 60}s`
      : `${secs}s`;
  })();

  const suggestedQuestions = [
    'Summarise this document',
    'What are the key findings?',
    'Extract financial metrics',
    'List all tables and figures',
    'Who are the main entities?',
    'What are the conclusions?',
  ];

  const handleSuggestedClick = (q) => {
    if (onQueryChange) onQueryChange(q);
    if (onSubmit) onSubmit(q);
  };

  const handleCopyText = (text) => {
    navigator.clipboard.writeText(text).catch(() => {});
  };

  const isGenerating = currentQueryStage && currentQueryStage !== 'completed';

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        overflow: 'hidden',
      }}
    >
      {/* ── Compact Single-Line Header Strip ──────────────────── */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          padding: '0 16px',
          height: '42px',
          borderBottom: '1px solid var(--border-subtle)',
          background: 'var(--bg-panel)',
          flexShrink: 0,
          flexWrap: 'nowrap',
          overflowX: 'auto',
          scrollbarWidth: 'none',
        }}
      >
        {/* Back to Home Button */}
        <button
          onClick={onReupload}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 4,
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: 6,
            color: 'var(--text-primary)',
            padding: '4px 10px',
            fontSize: '12px',
            fontWeight: 600,
            cursor: 'pointer',
            flexShrink: 0,
            transition: 'all 0.15s',
          }}
          title="Back to Home"
          onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.08)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; }}
        >
          <ChevronLeft size={14} />
          <span>Home</span>
        </button>

        <div style={{ width: 1, height: 14, background: 'var(--border-subtle)', flexShrink: 0 }} />

        {/* Status dot */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
          <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--color-success)' }} />
          <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--color-success)' }}>Ready</span>
        </div>

        <div style={{ width: 1, height: 14, background: 'var(--border-subtle)', flexShrink: 0 }} />

        {/* Document Selector Dropdown */}
        {processedDocs && processedDocs.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
            <FileText size={14} style={{ color: 'var(--color-accent)', flexShrink: 0 }} />
            <select
              value={activeDoc?.id || ''}
              onChange={(e) => {
                const docId = parseInt(e.target.value);
                const target = uploadedFiles.find((f) => f.id === docId);
                if (target && onSelectDocument) {
                  onSelectDocument(target);
                }
              }}
              style={{
                background: 'rgba(255,255,255,0.05)',
                border: '1px solid rgba(255,255,255,0.12)',
                borderRadius: '5px',
                color: '#fff',
                padding: '3px 8px',
                fontSize: '0.78rem',
                fontWeight: 600,
                cursor: 'pointer',
                outline: 'none',
                maxWidth: '220px',
                height: '28px',
              }}
              aria-label="Select document for AI chat"
            >
              {processedDocs.map((doc) => (
                <option key={doc.id} value={doc.id} style={{ background: '#181b28', color: '#fff' }}>
                  {doc.original_filename} ({doc.page_count ? `${doc.page_count} pg` : 'Ready'})
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Stats pills */}
        {[
          pageCount && `${pageCount} pg`,
          chunkCount && `${chunkCount} chunks`,
          processingTime && `${processingTime}`,
        ]
          .filter(Boolean)
          .map((label) => (
            <span
              key={label}
              style={{
                fontSize: '10px',
                color: 'var(--text-muted)',
                fontFamily: 'var(--font-mono)',
                background: 'rgba(255,255,255,0.03)',
                padding: '2px 6px',
                borderRadius: '4px',
                flexShrink: 0,
              }}
            >
              {label}
            </span>
          ))}

        <div style={{ flex: 1 }} />

        {/* Actions on right */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
          <button
            onClick={() => {
              if (window.confirm("Delete this document and all associated data?")) {
                onDelete?.(activeDoc?.id);
              }
            }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              background: 'none',
              border: '1px solid rgba(239,68,68,0.18)',
              borderRadius: 5,
              color: '#ef4444',
              padding: '3px 8px',
              fontSize: '11px',
              fontWeight: 600,
              cursor: 'pointer',
              height: '28px',
            }}
            title="Delete current document"
          >
            <Trash2 size={12} />
            <span>Delete</span>
          </button>

          <button
            onClick={onReupload}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              background: 'rgba(59,130,246,0.1)',
              border: '1px solid rgba(59,130,246,0.25)',
              borderRadius: 5,
              color: '#3b82f6',
              padding: '3px 10px',
              fontSize: '11px',
              fontWeight: 600,
              cursor: 'pointer',
              height: '28px',
            }}
            title="Upload new document"
          >
            <UploadCloud size={13} />
            <span>Upload</span>
          </button>
        </div>
      </div>

      {/* ── Main Split Layout: PDF (splitWidth%) | Resizer | Chat (100-splitWidth%) ────────── */}
      <div
        ref={containerGridRef}
        style={{
          display: 'flex',
          flexDirection: 'row',
          flex: 1,
          overflow: 'hidden',
          minHeight: 0,
          userSelect: isResizing ? 'none' : 'auto',
        }}
        className="ready-workspace-grid"
      >
        {/* ── LEFT: PDF Viewer ───────────────────────────────── */}
        <div
          style={{
            width: `${splitWidth}%`,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            background: 'var(--bg-primary)',
            flexShrink: 0,
          }}
        >
          {/* PDF Toolbar */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '10px 16px',
              borderBottom: '1px solid var(--border-subtle)',
              background: 'var(--bg-panel)',
              flexShrink: 0,
              flexWrap: 'wrap',
            }}
          >
            <BookOpen size={14} style={{ color: 'var(--color-accent)', flexShrink: 0 }} />
            <span style={{ fontSize: '11px', fontWeight: 700, color: '#fff', flex: 1 }}>
              {activeDoc?.original_filename || 'Document'}
            </span>

            {/* PDF search (inline) */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid rgba(255,255,255,0.06)',
                borderRadius: 6,
                padding: '4px 10px',
              }}
            >
              <Search size={11} style={{ color: 'var(--text-muted)' }} />
              <input
                type="text"
                placeholder="Search..."
                value={pdfSearchQuery}
                onChange={(e) => setPdfSearchQuery(e.target.value)}
                style={{
                  background: 'none',
                  border: 'none',
                  outline: 'none',
                  color: 'var(--text-primary)',
                  fontSize: '11px',
                  width: '80px',
                }}
              />
            </div>

            {/* Zoom controls */}
            <button
              onClick={() => setZoomLevel((p) => Math.max(40, p - 25))}
              style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
              aria-label="Zoom out"
            >
              <ZoomOut size={13} />
            </button>
            <span style={{ fontSize: '10px', fontFamily: 'monospace', color: 'var(--text-secondary)' }}>
              {zoomLevel}%
            </span>
            <button
              onClick={() => setZoomLevel((p) => Math.min(250, p + 25))}
              style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
              aria-label="Zoom in"
            >
              <ZoomIn size={13} />
            </button>
            <button
              onClick={handleFitToWidth}
              title="Auto-fit page to layout width"
              style={{
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: '4px',
                color: 'var(--text-secondary)',
                padding: '3px 7px',
                fontSize: '10px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                marginLeft: '4px'
              }}
            >
              <Maximize2 size={11} /> Fit Width
            </button>
          </div>

          {/* Canvas area */}
          <div
            ref={pdfContainerRef}
            style={{
              flex: 1,
              overflowY: 'auto',
              display: 'flex',
              justifyContent: 'center',
              padding: '20px',
              background: 'rgba(0,0,0,0.2)',
            }}
          >
            {pdfDoc ? (
              <div style={{ position: 'relative' }}>
                <canvas
                  ref={canvasRef}
                  style={{ borderRadius: 2, boxShadow: '0 4px 20px rgba(0,0,0,0.5)' }}
                />
                {/* Highlight overlays */}
                {highlights.map((h, i) => (
                  <div
                    key={i}
                    style={{
                      position: 'absolute',
                      top: h.y,
                      left: h.x,
                      width: h.width,
                      height: h.height,
                      background: 'rgba(59,130,246,0.25)',
                      border: '2px solid rgba(59,130,246,0.7)',
                      borderRadius: 2,
                      pointerEvents: 'none',
                    }}
                  />
                ))}
              </div>
            ) : pdfTextContent ? (
              <div
                style={{
                  width: '100%',
                  height: '100%',
                  overflowY: 'auto',
                  padding: '20px',
                  background: 'var(--bg-panel)',
                  color: 'var(--text-primary)',
                  fontFamily: 'monospace',
                  fontSize: '12px',
                  lineHeight: '1.6',
                  whiteSpace: 'pre-wrap',
                  borderRadius: '6px',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                {pdfTextContent}
              </div>
            ) : pdfLoading ? (
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 16,
                  height: '100%',
                  color: 'var(--text-disabled)',
                }}
              >
                <Loader2 size={32} style={{ color: 'var(--color-accent)', animation: 'spin 1s linear infinite' }} />
                <span style={{ fontSize: '12px', textAlign: 'center' }}>
                  Loading document preview...
                </span>
              </div>
            ) : pdfError ? (
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 12,
                  height: '100%',
                  color: 'var(--text-secondary)',
                  padding: '20px',
                }}
              >
                <AlertCircle size={32} style={{ color: 'var(--color-failure)' }} />
                <span style={{ fontSize: '12px', textAlign: 'center', maxWidth: '80%' }}>
                  {pdfError}
                </span>
                {onRetryLoadPdf && (
                  <button
                    onClick={onRetryLoadPdf}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                      background: 'rgba(255,255,255,0.05)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: '6px',
                      color: 'var(--text-primary)',
                      padding: '6px 14px',
                      fontSize: '11px',
                      cursor: 'pointer',
                    }}
                  >
                    <RotateCw size={12} /> Retry Preview
                  </button>
                )}
              </div>
            ) : (
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 16,
                  height: '100%',
                  color: 'var(--text-disabled)',
                }}
              >
                <FileText size={36} style={{ opacity: 0.3 }} />
                <span style={{ fontSize: '12px', textAlign: 'center' }}>
                  No document preview available.
                </span>
              </div>
            )}
          </div>

          {/* Page navigation footer */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '10px 16px',
              borderTop: '1px solid var(--border-subtle)',
              background: 'var(--bg-panel)',
              flexShrink: 0,
            }}
          >
            <button
              disabled={activePdfPage <= 1}
              onClick={() => setActivePdfPage((p) => Math.max(1, p - 1))}
              style={{ background: 'none', border: 'none', color: activePdfPage <= 1 ? 'var(--text-disabled)' : 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontSize: '12px' }}
            >
              <ChevronLeft size={14} /> Prev
            </button>
            <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontFamily: 'monospace' }}>
              Page {activePdfPage}{pageCount ? ` / ${pageCount}` : ''}
            </span>
            <button
              disabled={pageCount ? activePdfPage >= pageCount : false}
              onClick={() => setActivePdfPage((p) => (pageCount ? Math.min(pageCount, p + 1) : p + 1))}
              style={{ background: 'none', border: 'none', color: (pageCount && activePdfPage >= pageCount) ? 'var(--text-disabled)' : 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontSize: '12px' }}
            >
              Next <ChevronRight size={14} />
            </button>
          </div>
        </div>

        {/* ── Resizable Splitter Handle (LeetCode style) ──────── */}
        <div
          onMouseDown={startResizing}
          title="Drag to resize PDF and AI Chat panels"
          style={{
            width: '6px',
            cursor: 'col-resize',
            background: isResizing ? 'rgba(59,130,246,0.6)' : 'var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            position: 'relative',
            zIndex: 10,
            transition: 'background 0.15s ease',
            flexShrink: 0,
          }}
          onMouseEnter={(e) => { if (!isResizing) e.currentTarget.style.background = 'rgba(59,130,246,0.4)'; }}
          onMouseLeave={(e) => { if (!isResizing) e.currentTarget.style.background = 'var(--border-subtle)'; }}
        >
          <div
            style={{
              width: '2px',
              height: '32px',
              borderRadius: '1px',
              background: isResizing ? '#fff' : 'rgba(255,255,255,0.25)',
            }}
          />
        </div>

        {/* ── RIGHT: AI Chat Workbench ────────────────────────── */}
        <div
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            background: 'var(--bg-primary)',
            minWidth: 0,
          }}
        >
          {/* Chat header */}
          <div
            style={{
              padding: '12px 20px',
              borderBottom: '1px solid var(--border-subtle)',
              background: 'var(--bg-panel)',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              flexShrink: 0,
            }}
          >
            <Sparkles size={14} style={{ color: 'var(--color-accent)' }} />
            <span style={{ fontSize: '12px', fontWeight: 700, color: '#fff' }}>
              AI Chat
            </span>
            {isGenerating && (
              <span
                style={{
                  marginLeft: 'auto',
                  fontSize: '10px',
                  color: 'var(--color-accent)',
                  fontFamily: 'monospace',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                }}
              >
                <span
                  style={{
                    width: 6,
                    height: 6,
                    borderRadius: '50%',
                    background: 'var(--color-accent)',
                    animation: 'chatPulse 1s ease infinite',
                  }}
                />
                {currentQueryStage?.toUpperCase()} · {queryTimer?.toFixed(1)}s
              </span>
            )}
          </div>

          {/* Messages list */}
          <div
            style={{
              flex: 1,
              overflowY: 'auto',
              padding: '20px',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px',
            }}
          >
            {chatThread.map((msg, idx) => {
              const isUser = msg.role === 'user';
              return (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    justifyContent: isUser ? 'flex-end' : 'flex-start',
                    alignItems: 'flex-start',
                    gap: '10px',
                  }}
                >
                  {!isUser && (
                    <div
                      style={{
                        width: 28,
                        height: 28,
                        borderRadius: '50%',
                        background: 'rgba(99,102,241,0.12)',
                        border: '1px solid rgba(99,102,241,0.2)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                      }}
                    >
                      <Sparkles size={12} style={{ color: 'var(--color-accent)' }} />
                    </div>
                  )}
                  <div
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '4px',
                      maxWidth: '85%',
                    }}
                  >
                    <div
                      style={{
                        padding: '12px 16px',
                        borderRadius: isUser ? '12px 12px 4px 12px' : '12px 12px 12px 4px',
                        background: isUser
                          ? 'var(--color-accent)'
                          : 'rgba(255,255,255,0.03)',
                        border: isUser
                          ? 'none'
                          : '1px solid rgba(255,255,255,0.06)',
                        color: '#fff',
                        fontSize: '0.85rem',
                        lineHeight: 1.6,
                        position: 'relative',
                      }}
                    >
                      <FormattedMessage content={msg.content} onCitationClick={onCitationClick} />

                      {/* Copy / Regenerate actions for assistant messages */}
                      {!isUser && !msg.isStreaming && (
                        <div
                          style={{
                            display: 'flex',
                            gap: 4,
                            marginTop: 8,
                            borderTop: '1px solid rgba(255,255,255,0.05)',
                            paddingTop: 8,
                          }}
                        >
                          <button
                            onClick={() => handleCopyText(msg.content)}
                            style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontSize: '10px', padding: '2px 6px', borderRadius: 4, transition: 'color 0.15s' }}
                            title="Copy answer"
                          >
                            <Copy size={10} /> Copy
                          </button>
                        </div>
                      )}
                    </div>

                    {/* Citation chips */}
                    {!isUser && msg.citations && msg.citations.length > 0 && (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 4 }}>
                        {msg.citations.map((c, ci) => (
                          <button
                            key={ci}
                            onClick={() => onCitationClick && onCitationClick(c)}
                            style={{
                              background: 'rgba(16,185,129,0.08)',
                              border: '1px solid rgba(16,185,129,0.2)',
                              borderRadius: 6,
                              color: 'var(--color-success)',
                              fontSize: '10px',
                              padding: '3px 10px',
                              cursor: 'pointer',
                              fontFamily: 'monospace',
                              transition: 'all 0.15s',
                            }}
                            onMouseEnter={(e) => {
                              e.currentTarget.style.background = 'rgba(16,185,129,0.15)';
                            }}
                            onMouseLeave={(e) => {
                              e.currentTarget.style.background = 'rgba(16,185,129,0.08)';
                            }}
                            title={`Jump to page ${c.page}`}
                          >
                            p.{c.page}
                          </button>
                        ))}
                      </div>
                    )}

                    <span style={{ fontSize: '9px', color: 'var(--text-disabled)', alignSelf: isUser ? 'flex-end' : 'flex-start', fontFamily: 'monospace' }}>
                      {msg.timestamp}
                    </span>
                  </div>
                </div>
              );
            })}
            <div ref={messagesEndRef} />
          </div>

          {/* Suggested questions — shown on first load */}
          {chatThread.length <= 1 && (
            <div style={{ padding: '0 20px 12px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <span
                style={{
                  fontSize: '10px',
                  color: 'var(--text-disabled)',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                }}
              >
                Suggested Questions
              </span>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {suggestedQuestions.map((q) => (
                  <button
                    key={q}
                    onClick={() => handleSuggestedClick(q)}
                    disabled={isGenerating}
                    style={{
                      background: 'rgba(255,255,255,0.02)',
                      border: '1px solid rgba(255,255,255,0.06)',
                      borderRadius: '6px',
                      padding: '6px 12px',
                      fontSize: '11px',
                      color: 'var(--text-secondary)',
                      cursor: isGenerating ? 'not-allowed' : 'pointer',
                      transition: 'all 0.15s',
                      opacity: isGenerating ? 0.5 : 1,
                    }}
                    onMouseEnter={(e) => !isGenerating && (e.currentTarget.style.borderColor = 'rgba(99,102,241,0.3)')}
                    onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)')}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Chat input bar */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (chatQuery.trim() && !isGenerating) onSubmit();
            }}
            style={{
              padding: '14px 20px',
              borderTop: '1px solid var(--border-subtle)',
              background: 'var(--bg-panel)',
              display: 'flex',
              gap: '10px',
              flexShrink: 0,
              alignItems: 'center',
            }}
          >
            <input
              type="text"
              placeholder="Ask anything about this document..."
              value={chatQuery}
              onChange={(e) => onQueryChange && onQueryChange(e.target.value)}
              disabled={isGenerating}
              style={{
                flex: 1,
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: '8px',
                padding: '0 16px',
                height: '40px',
                color: '#fff',
                outline: 'none',
                fontSize: '0.85rem',
                transition: 'border-color 0.2s',
              }}
              onFocus={(e) => (e.currentTarget.style.borderColor = 'rgba(99,102,241,0.4)')}
              onBlur={(e) => (e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)')}
            />

            {isGenerating ? (
              <button
                type="button"
                onClick={onStopGeneration}
                style={{
                  height: 40,
                  padding: '0 14px',
                  borderRadius: 8,
                  background: 'rgba(239,68,68,0.08)',
                  border: '1px solid rgba(239,68,68,0.2)',
                  color: '#ef4444',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  fontSize: '12px',
                  fontWeight: 600,
                  transition: 'all 0.15s',
                }}
              >
                <StopCircle size={14} /> Stop
              </button>
            ) : (
              <Button
                type="submit"
                variant="primary"
                disabled={!chatQuery.trim()}
                style={{ height: 40, padding: '0 16px', borderRadius: 8 }}
              >
                <Send size={14} />
              </Button>
            )}
          </form>
        </div>
      </div>

      {/* Responsive CSS */}
      <style>{`
        @keyframes chatPulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }

        /* Tablet: stack Chat above PDF */
        @media (max-width: 1023px) {
          .ready-workspace-grid {
            grid-template-columns: 1fr !important;
            grid-template-rows: auto 1fr;
          }
          .ready-workspace-grid > div:first-child {
            order: 2;
            max-height: 40vh;
          }
          .ready-workspace-grid > div:last-child {
            order: 1;
          }
        }

        /* Mobile: single column tabs */
        @media (max-width: 767px) {
          .ready-workspace-grid > div:first-child {
            max-height: 50vh;
          }
        }
      `}</style>
    </div>
  );
};

export default ReadyWorkspace;
