import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { usePipeline } from '../contexts/PipelineContext';
import { useDocument } from '../contexts/DocumentContext';
import { useWorkspace } from '../contexts/WorkspaceContext';
import {
  createQueryPipelineV1,
  fetchQueryPipelineAnswerV1,
} from '../services/search';
import { fetchUploadedFiles, fetchPdfContent, deleteDocument } from '../services/documents';
import {
  fetchPipelineDetails,
} from '../services/pipelines';
import { apiClient } from '../services/apiClient';

import { useNotification } from '../contexts/NotificationContext';
import ConfirmDialog from '../components/ui/ConfirmDialog';
import { UploadWorkspace } from '../components/workspace/upload/UploadWorkspace';
import { ProcessingWorkspace } from '../components/workspace/pipeline/ProcessingWorkspace';
import { ReadyWorkspace } from '../components/workspace/chat/ReadyWorkspace';
import { DeveloperPanelTabs } from '../components/workspace/DeveloperPanelTabs';
import BottomDrawer from '../components/layout/BottomDrawer';

/**
 * Workspace State Machine
 *
 *  WORKSPACE_EMPTY      — no document selected / no pipeline
 *  WORKSPACE_PROCESSING — pipeline is queued | running | waiting | paused | failed
 *  WORKSPACE_READY      — pipeline is completed
 *
 * Transitions:
 *  WORKSPACE_EMPTY      → upload started     → WORKSPACE_PROCESSING
 *  WORKSPACE_PROCESSING → pipeline completed → WORKSPACE_READY
 *  WORKSPACE_PROCESSING → pipeline failed    → WORKSPACE_PROCESSING (error state)
 *  WORKSPACE_READY      → re-upload          → WORKSPACE_PROCESSING
 *  WORKSPACE_READY      → remove document    → WORKSPACE_EMPTY
 */

const WS = {
  EMPTY:      'WORKSPACE_EMPTY',
  PROCESSING: 'WORKSPACE_PROCESSING',
  READY:      'WORKSPACE_READY',
};

const pipelineStatusToWsState = (status) => {
  if (!status) return WS.EMPTY;
  const s = status.toLowerCase();
  if (s === 'completed' || s === 'processed') return WS.READY;
  return WS.PROCESSING;
};

export const WorkspaceHome = ({ activeView = 'workspace', devPanelOpen, onToggleDevPanel, onNavigateToView }) => {
  const {
    selectedPipelineId,
    setSelectedPipelineId,
    pipelines,
    timelineEvents,
    timelineLoading,
    timelineError,
    refreshTrigger,
    onRetryTask,
    replayMode, replayIndex, replaySnapshots,
  } = usePipeline();

  const { selectedDocumentId, setSelectedDocumentId, uploadedFiles, setUploadedFiles } = useDocument();
  const { selectDocument } = useWorkspace();

  // ── Workspace state machine ───────────────────────────────
  const [workspaceState, setWorkspaceState] = useState(WS.EMPTY);

  // ── Local document/pipeline metadata ─────────────────────
  const [activeDag, setActiveDag] = useState(null);
  const [pipelineMetadata, setPipelineMetadata] = useState(null);

  // ── PDF rendering ─────────────────────────────────────────
  const canvasRef = useRef(null);
  const [pdfDoc, setPdfDoc] = useState(null);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [pdfError, setPdfError] = useState(null);
  const [pdfTextContent, setPdfTextContent] = useState(null);
  const [pageCount, setPageCount] = useState(1);
  const [activePdfPage, setActivePdfPage] = useState(1);
  const [zoomLevel, setZoomLevel] = useState(100);
  const [highlights, setHighlights] = useState([]);

  // ── Chat state ────────────────────────────────────────────
  const [chatQuery, setChatQuery] = useState('');
  const [chatThread, setChatThread] = useState([
    {
      role: 'assistant',
      content: 'Document indexed. Ask any question to begin.',
      timestamp: new Date().toLocaleTimeString(),
    },
  ]);
  const [currentQueryStage, setCurrentQueryStage] = useState('');
  const [queryTimer, setQueryTimer] = useState(0.0);
  const [activeAnswerDetails, setActiveAnswerDetails] = useState(null);

  // Streaming stop ref
  const eventSourceRef = useRef(null);

  // ─────────────────────────────────────────────────────────
  // Load documents library (polling)
  // ─────────────────────────────────────────────────────────
  useEffect(() => {
    const load = async () => {
      try {
        const files = await fetchUploadedFiles();
        setUploadedFiles(prev => {
          if (JSON.stringify(prev) === JSON.stringify(files)) return prev;
          return files || [];
        });
      } catch (err) {
        console.error('Error loading files', err);
      }
    };
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, [setUploadedFiles]);

  // ─────────────────────────────────────────────────────────
  // Restore persisted selection
  // ─────────────────────────────────────────────────────────
  useEffect(() => {
    const docId = localStorage.getItem('scaleflow_active_doc');
    const zoom  = localStorage.getItem('scaleflow_zoom');
    const page  = localStorage.getItem('scaleflow_pdf_page');
    if (docId) setSelectedDocumentId(parseInt(docId));
    if (zoom)  setZoomLevel(parseInt(zoom));
    if (page)  setActivePdfPage(parseInt(page));
  }, [setSelectedDocumentId]);

  // ─────────────────────────────────────────────────────────
  // Persist UX choices
  // ─────────────────────────────────────────────────────────
  useEffect(() => {
    localStorage.setItem('scaleflow_zoom', zoomLevel);
  }, [zoomLevel]);

  useEffect(() => {
    localStorage.setItem('scaleflow_pdf_page', activePdfPage);
  }, [activePdfPage]);

  // Auto-select latest PROCESSED document when entering AI Chat if no active selection or if selected doc is failed
  useEffect(() => {
    if (activeView === 'chat' && uploadedFiles && uploadedFiles.length > 0) {
      const activeFile = uploadedFiles.find(f => f.id === selectedDocumentId);
      const activeStatus = (activeFile?.status || '').toLowerCase();
      
      // If no document selected, or selected document failed/deleted, auto-select first PROCESSED document
      if (!selectedDocumentId || activeStatus === 'failed' || activeStatus === 'blocked' || activeStatus === 'cancelled') {
        const processedDoc = uploadedFiles.find(f => {
          const s = (f.status || '').toLowerCase();
          return s === 'completed' || s === 'processed';
        });
        
        if (processedDoc) {
          setSelectedDocumentId(processedDoc.id);
          selectDocument(processedDoc.id);
        } else {
          // If no processed document exists yet, select a processing one to display the parsing status
          const processingDoc = uploadedFiles.find(f => {
            const s = (f.status || '').toLowerCase();
            return s !== 'failed' && s !== 'blocked' && s !== 'cancelled';
          });
          if (processingDoc && processingDoc.id !== selectedDocumentId) {
            setSelectedDocumentId(processingDoc.id);
            selectDocument(processingDoc.id);
          }
        }
      }
    }
  }, [activeView, selectedDocumentId, uploadedFiles, setSelectedDocumentId, selectDocument]);

  // ─────────────────────────────────────────────────────────
  // Derive workspace state from selected document + pipeline
  // Automatic transitions — no manual navigation required
  // ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (!selectedDocumentId) {
      setWorkspaceState(WS.EMPTY);
      return;
    }

    localStorage.setItem('scaleflow_active_doc', selectedDocumentId);

    const doc   = uploadedFiles.find((f) => f.id === selectedDocumentId);
    const assoc = pipelines.find(
      (p) => p.file_id === selectedDocumentId || (doc && (p.file_id === doc.id || p.id === doc.pipeline_id))
    );

    const targetPipelineId = assoc ? assoc.id : (doc ? doc.pipeline_id : null);
    if (targetPipelineId) {
      setSelectedPipelineId(targetPipelineId);
    }

    const effectiveStatus = assoc ? assoc.status : (doc ? doc.status : null);
    if (effectiveStatus) {
      const nextState = pipelineStatusToWsState(effectiveStatus);
      setWorkspaceState(nextState);
    } else {
      // Default to processing state if status is pending/unknown
      setWorkspaceState(WS.PROCESSING);
    }
  }, [selectedDocumentId, uploadedFiles, pipelines, setSelectedPipelineId]);

  // ─────────────────────────────────────────────────────────
  // Poll pipeline details (DAG + metadata) every 3s
  // ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (!selectedPipelineId || replayMode) return;
    
    // Check current status before starting polling
    const currentStatus = activeDag?.pipeline?.status?.toLowerCase();
    const isTerminal = currentStatus && ['completed', 'cancelled', 'failed'].includes(currentStatus);
    
    const load = async () => {
      try {
        const details = await fetchPipelineDetails(selectedPipelineId);
        setActiveDag(details);
        // Auto-transition on status change from backend
        const backendStatus = details?.pipeline?.status;
        if (backendStatus) {
          setWorkspaceState(pipelineStatusToWsState(backendStatus));
        }
      } catch (e) {
        console.error('fetchPipelineDetails failed', e);
      }
      try {
        const metaRes = await apiClient.get(`/pipelines/${selectedPipelineId}/metadata`);
        setPipelineMetadata(metaRes.data);
      } catch (_) { /* 404 is expected when metadata not ready */ }
    };
    
    load();
    
    if (isTerminal) {
      return; // Do not schedule interval if status is already completed, cancelled, or failed
    }

    const interval = setInterval(async () => {
      try {
        const details = await fetchPipelineDetails(selectedPipelineId);
        setActiveDag(prev => {
          if (JSON.stringify(prev) === JSON.stringify(details)) return prev;
          return details;
        });
        const backendStatus = details?.pipeline?.status;
        if (backendStatus) {
          setWorkspaceState(pipelineStatusToWsState(backendStatus));
          // If status becomes completed/failed/cancelled, clear interval
          const s = backendStatus.toLowerCase();
          if (['completed', 'failed', 'cancelled'].includes(s)) {
            clearInterval(interval);
          }
        }
      } catch (e) {
        console.error('fetchPipelineDetails failed during poll', e);
      }
      try {
        const metaRes = await apiClient.get(`/pipelines/${selectedPipelineId}/metadata`);
        setPipelineMetadata(metaRes.data);
      } catch (_) {}
    }, 3000);

    return () => clearInterval(interval);
  }, [selectedPipelineId, refreshTrigger, replayMode, activeDag?.pipeline?.status]);

  // ─────────────────────────────────────────────────────────
  // Replay-aware DAG snapshot (for Developer Panel → Replay tab)
  // ─────────────────────────────────────────────────────────
  const currentActiveDag = useMemo(() => {
    if (!replayMode || !replaySnapshots || replayIndex < 0 || !activeDag) return activeDag;
    const snapshot = replaySnapshots[replayIndex];
    const replayedTasks = (activeDag.tasks || []).map((t) => {
      const snapTask = snapshot.taskStates[String(t.id)];
      return snapTask
        ? { ...t, status: snapTask.status, assigned_worker_id: snapTask.workerId, retry_count: snapTask.retryCount }
        : t;
    });
    return {
      ...activeDag,
      pipeline: {
        ...activeDag.pipeline,
        status: replayedTasks.every((t) => t.status === 'completed')
          ? 'completed'
          : replayedTasks.some((t) => t.status === 'failed')
          ? 'failed'
          : 'running',
      },
      tasks: replayedTasks,
    };
  }, [replayMode, replaySnapshots, replayIndex, activeDag]);

  // ─────────────────────────────────────────────────────────
  // Load PDF via pdfjs
  // ─────────────────────────────────────────────────────────
  const handleLoadPdf = useCallback(async () => {
    if (!selectedDocumentId || workspaceState !== WS.READY) {
      setPdfDoc(prev => {
        if (prev) { try { prev.destroy(); } catch(e) {} }
        return null;
      });
      setPdfError(null);
      setPdfTextContent(null);
      return;
    }
    setPdfLoading(true);
    setPdfError(null);
    setPdfTextContent(null);
    try {
      const blob        = await fetchPdfContent(selectedDocumentId);
      const arrayBuffer = await blob.arrayBuffer();
      
      let pdfjsModule;
      try {
        pdfjsModule = await import('pdfjs-dist');
      } catch (e1) {
        pdfjsModule = await import('pdfjs-dist/build/pdf');
      }
      const pdfjs = pdfjsModule.default || pdfjsModule;

      if (pdfjs.GlobalWorkerOptions) {
        pdfjs.GlobalWorkerOptions.workerSrc = window.location.origin + '/pdf.worker.min.mjs';
      }

      let loadingTask;
      try {
        loadingTask = pdfjs.getDocument({
          data: new Uint8Array(arrayBuffer),
          isEvalSupported: false,
        });
        const pdf = await loadingTask.promise;
        setPdfDoc(prev => {
          if (prev && prev !== pdf) { try { prev.destroy(); } catch(e) {} }
          return pdf;
        });
        setPageCount(pdf.numPages || 1);
        setActivePdfPage(1);
      } catch (workerErr) {
        if (workerErr?.message?.includes('Worker version') || workerErr?.message?.includes('API version')) {
          console.warn('[PDFJS] Version mismatch on local worker, switching to CDN worker matching pdfjs.version', workerErr);
          const version = pdfjs.version || '6.1.200';
          pdfjs.GlobalWorkerOptions.workerSrc = `https://cdn.jsdelivr.net/npm/pdfjs-dist@${version}/build/pdf.worker.min.mjs`;
          loadingTask = pdfjs.getDocument({
            data: new Uint8Array(arrayBuffer),
            isEvalSupported: false,
          });
          const pdf = await loadingTask.promise;
          setPdfDoc(prev => {
          if (prev && prev !== pdf) { try { prev.destroy(); } catch(e) {} }
          return pdf;
        });
          setPageCount(pdf.numPages || 1);
          setActivePdfPage(1);
        } else {
          throw workerErr;
        }
      }
    } catch (err) {
      console.error('Error loading PDF via pdfjs-dist', err);
      // Fallback: check if content can be displayed as text preview
      try {
        const blob = await fetchPdfContent(selectedDocumentId);
        const text = await blob.text();
        if (text && text.trim() && !text.includes('%PDF')) {
          setPdfTextContent(text);
        } else {
          setPdfError(err.message || 'Could not load PDF document preview.');
        }
      } catch (e2) {
        setPdfError(err.message || 'Could not load document preview.');
      }
    } finally {
      setPdfLoading(false);
    }
  }, [selectedDocumentId, workspaceState]);

  useEffect(() => {
    handleLoadPdf();
  }, [handleLoadPdf]);

  // ─────────────────────────────────────────────────────────
  // Render canvas page
  // ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (!pdfDoc || !canvasRef.current) return;
    let renderTask = null;
    const renderPage = async () => {
      try {
        const page     = await pdfDoc.getPage(activePdfPage);
        const viewport = page.getViewport({ scale: zoomLevel / 100 });
        const canvas   = canvasRef.current;
        const ctx      = canvas.getContext('2d');
        canvas.height  = viewport.height;
        canvas.width   = viewport.width;
        renderTask     = page.render({ canvasContext: ctx, viewport });
        await renderTask.promise;
      } catch (err) {
        if (err?.name !== 'RenderingCancelledException') {
          console.error('Error rendering PDF page', err);
        }
      }
    };
    renderPage();
    return () => {
      if (renderTask) {
        try {
          renderTask.cancel();
        } catch (_) {}
      }
    };
  }, [pdfDoc, activePdfPage, zoomLevel]);

  // ─────────────────────────────────────────────────────────
  // Query stage timer
  // ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (!currentQueryStage || currentQueryStage === 'completed') return;
    const timer = setInterval(() => setQueryTimer((p) => p + 0.05), 50);
    return () => clearInterval(timer);
  }, [currentQueryStage]);

  // ─────────────────────────────────────────────────────────
  // Fetch answer details after query completes
  // ─────────────────────────────────────────────────────────
  const fetchAnswerExplain = async (pipelineId) => {
    try {
      const ans = await fetchQueryPipelineAnswerV1(pipelineId);
      setActiveAnswerDetails(ans);
    } catch (e) {
      console.error('Error fetching answer details', e);
    }
  };

  // ─────────────────────────────────────────────────────────
  // Submit chat query (SSE stream)
  // ─────────────────────────────────────────────────────────
  const handleSendQuery = useCallback(async (overrideQuery) => {
    const userMsg = typeof overrideQuery === 'string' ? overrideQuery : chatQuery;
    if (!userMsg.trim()) return;

    setChatQuery('');
    setQueryTimer(0.0);
    setCurrentQueryStage('intent');

    setChatThread((prev) => [
      ...prev,
      { role: 'user', content: userMsg, timestamp: new Date().toLocaleTimeString() },
    ]);

    const tempMsgId = `stream-${Date.now()}`;
    setChatThread((prev) => [
      ...prev,
      { id: tempMsgId, role: 'assistant', content: 'Processing query...', isStreaming: true, timestamp: new Date().toLocaleTimeString() },
    ]);

    try {
      const qpPayload = {
        query: userMsg,
        top_k: 5,
        document_ids: [selectedDocumentId],
      };
      const res = await createQueryPipelineV1(qpPayload);
      const pipeId = res.pipeline_id;
      setCurrentQueryStage('embedding');

      const es = new EventSource(
        `${process.env.REACT_APP_API_URL || 'http://127.0.0.1:5000'}/api/v1/query-pipelines/${pipeId}/stream`
      );
      eventSourceRef.current = es;
      let accumulator = '';

      es.addEventListener('stage', (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.stage === 'retrieving') setCurrentQueryStage('vector');
          else if (data.stage === 'reranking') setCurrentQueryStage('fusion');
          else if (data.stage === 'generating') setCurrentQueryStage('llm');
        } catch (e) {
          console.warn('[SSE] Stage event parse error:', e, event.data);
        }
      });

      es.addEventListener('token', (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data && data.token !== undefined) {
            accumulator += data.token;
            setChatThread((prev) =>
              prev.map((m) => (m.id === tempMsgId ? { ...m, content: accumulator, isStreaming: true } : m))
            );
          }
        } catch (e) {
          console.warn('[SSE] Token event parse error:', e, event.data);
        }
      });

      es.addEventListener('completed', () => {
        es.close();
        eventSourceRef.current = null;
        setCurrentQueryStage('completed');
        setChatThread((prev) =>
          prev.map((m) => (m.id === tempMsgId ? { ...m, isStreaming: false } : m))
        );
        fetchAnswerExplain(pipeId);
      });

      es.addEventListener('error', () => {
        es.close();
        eventSourceRef.current = null;
        setCurrentQueryStage('completed');
        setChatThread((prev) =>
          prev.map((m) =>
            m.id === tempMsgId
              ? { ...m, content: 'Streaming connection encountered an error.', isError: true, isStreaming: false }
              : m
          )
        );
      });
    } catch (err) {
      setCurrentQueryStage('completed');
      setChatThread((prev) => [
        ...prev.filter((m) => m.id !== tempMsgId),
        { role: 'assistant', content: `Error: ${err.message}`, isError: true, timestamp: new Date().toLocaleTimeString() },
      ]);
    }
  }, [chatQuery, selectedDocumentId]);

  const handleStopGeneration = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setCurrentQueryStage('completed');
    setChatThread((prev) =>
      prev.map((m) => (m.isStreaming ? { ...m, isStreaming: false, content: m.content + ' [stopped]' } : m))
    );
  }, []);

  const handleCitationClick = useCallback((citation) => {
    if (!citation) return;

    let targetPage = 1;
    let box = null;

    if (typeof citation === 'string') {
      const cleanId = citation.replace('chunk_', '');
      const foundCit = activeAnswerDetails?.citations?.find(
        (c) => (c.chunk_id && c.chunk_id.includes(cleanId)) || (c.id && String(c.id).includes(cleanId))
      );
      if (foundCit && foundCit.page) {
        targetPage = foundCit.page;
        box = foundCit.bounding_box || foundCit.bbox;
      } else {
        const cand = activeAnswerDetails?.retrieval?.candidates?.find(
          (c) => c.chunk_id && c.chunk_id.includes(cleanId)
        );
        if (cand && cand.page) {
          targetPage = cand.page;
        }
      }
    } else if (typeof citation === 'object') {
      targetPage = citation.page || citation.page_number || 1;
      box = citation.bounding_box || citation.bbox;
    }

    setActivePdfPage(targetPage);

    if (box) {
      setHighlights([box]);
    } else {
      setHighlights([{ x: 40, y: 80, width: 350, height: 70, page: targetPage }]);
    }
  }, [activeAnswerDetails]);

  // ─────────────────────────────────────────────────────────
  // Derived helpers
  // ─────────────────────────────────────────────────────────
  const activeDoc = uploadedFiles.find((f) => f.id === selectedDocumentId);

  const { addNotification } = useNotification();
  const [deleteConfirmDocId, setDeleteConfirmDocId] = useState(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  const handleSelectDocument = (doc) => {
    if (!doc) return;
    setSelectedDocumentId(doc.id);
    selectDocument(doc.id);

    const s = (doc.status || '').toLowerCase();
    if (s === 'failed' || s === 'blocked' || s === 'cancelled') {
      addNotification(`Document "${doc.original_filename}" failed processing. Redirecting to Pipeline Monitor.`, 'warning', 'system');
      if (onNavigateToView) {
        onNavigateToView('pipelines');
      }
    } else {
      if (onNavigateToView) {
        onNavigateToView('chat');
      }
    }
  };

  const handleOpenChat = (doc) => {
    if (!doc) return;
    const s = (doc.status || '').toLowerCase();
    if (s !== 'completed' && s !== 'processed') return;

    setSelectedDocumentId(doc.id);
    selectDocument(doc.id);

    const assoc = pipelines.find(
      (p) => p.file_id === doc.id || (doc && (p.file_id === doc.id || p.id === doc.pipeline_id))
    );
    const targetPipelineId = assoc ? assoc.id : doc.pipeline_id;
    if (targetPipelineId) {
      setSelectedPipelineId(targetPipelineId);
    }

    if (onNavigateToView) {
      onNavigateToView('chat');
    }
  };

  const handleInspectPipeline = (doc) => {
    if (!doc) return;
    setSelectedDocumentId(doc.id);
    selectDocument(doc.id);

    const assoc = pipelines.find(
      (p) => p.file_id === doc.id || (doc && (p.file_id === doc.id || p.id === doc.pipeline_id))
    );
    const targetPipelineId = assoc ? assoc.id : doc.pipeline_id;
    if (targetPipelineId) {
      setSelectedPipelineId(targetPipelineId);
    }

    if (onNavigateToView) {
      onNavigateToView('pipelines');
    }
  };

  const onRequestDeleteDocument = (docId) => {
    setDeleteConfirmDocId(docId || selectedDocumentId);
  };

  const handleConfirmWorkspaceDelete = async () => {
    if (!deleteConfirmDocId) return;
    const docId = deleteConfirmDocId;
    const docToDelete = uploadedFiles.find(f => f.id === docId) || activeDoc;
    const filename = docToDelete?.original_filename || `Document #${docId}`;
    setDeleteLoading(true);
    try {
      await deleteDocument(docId);
      addNotification(`Document "${filename}" was permanently deleted.`, 'danger', 'system');
      localStorage.removeItem('scaleflow_active_doc');
      setSelectedDocumentId(null);
      setSelectedPipelineId(null);
      setPdfDoc(null);
      setActiveDag(null);
      setWorkspaceState(WS.EMPTY);
      setDeleteConfirmDocId(null);
      const files = await fetchUploadedFiles();
      setUploadedFiles(files || []);
    } catch (err) {
      console.error('Delete failed:', err);
      addNotification(`Delete failed: ${err.message}`, 'error', 'system');
    } finally {
      setDeleteLoading(false);
    }
  };

  const handleReupload = () => {
    setWorkspaceState(WS.EMPTY);
    setSelectedDocumentId(null);
    setSelectedPipelineId(null);
    setPdfDoc(null);
    setActiveDag(null);
    localStorage.removeItem('scaleflow_active_doc');
    setChatThread([
      {
        role: 'assistant',
        content: 'Document indexed. Ask any question to begin.',
        timestamp: new Date().toLocaleTimeString(),
      },
    ]);
    if (onNavigateToView) {
      onNavigateToView('workspace');
    }
  };

  const handleUploadComplete = (newDoc) => {
    // Backend returned a new document; switch to PROCESSING and select it
    if (newDoc?.id) {
      setSelectedDocumentId(newDoc.id);
      selectDocument(newDoc.id);
    }
    setWorkspaceState(WS.PROCESSING);
    if (onNavigateToView) {
      onNavigateToView('chat');
    }
  };

  // ─────────────────────────────────────────────────────────
  // Render
  // ─────────────────────────────────────────────────────────
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        overflow: 'hidden',
        background: 'var(--bg-primary)',
      }}
    >
      {/* ── Primary Workspace (state-driven) ──────────────── */}
      <div style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>

        {activeView === 'workspace' ? (
          <UploadWorkspace
            uploadedFiles={uploadedFiles}
            onSelectDocument={handleSelectDocument}
            onUploadComplete={handleUploadComplete}
            onOpenChat={handleOpenChat}
            onInspectPipeline={handleInspectPipeline}
          />
        ) : (
          <>
            {workspaceState === WS.EMPTY && (
              <UploadWorkspace
                uploadedFiles={uploadedFiles}
                onSelectDocument={handleSelectDocument}
                onUploadComplete={handleUploadComplete}
                onOpenChat={handleOpenChat}
                onInspectPipeline={handleInspectPipeline}
              />
            )}

            {workspaceState === WS.PROCESSING && (
              <ProcessingWorkspace
                activeDag={currentActiveDag}
                selectedPipelineId={selectedPipelineId}
                activeDoc={activeDoc}
                timelineEvents={timelineEvents}
                timelineLoading={timelineLoading}
                timelineError={timelineError}
                onRetryTask={onRetryTask}
                onReupload={handleReupload}
                onDelete={onRequestDeleteDocument}
              />
            )}

            {workspaceState === WS.READY && (
              <ReadyWorkspace
                activeDoc={activeDoc}
                uploadedFiles={uploadedFiles}
                selectedDocumentId={selectedDocumentId}
                onSelectDocument={handleSelectDocument}
                activeDag={currentActiveDag}
                pipelineMetadata={pipelineMetadata}
                chatThread={chatThread}
                chatQuery={chatQuery}
                onQueryChange={setChatQuery}
                onSubmit={handleSendQuery}
                currentQueryStage={currentQueryStage}
                queryTimer={queryTimer}
                activeAnswerDetails={activeAnswerDetails}
                onStopGeneration={handleStopGeneration}
                onCitationClick={handleCitationClick}
                pdfDoc={pdfDoc}
                pdfLoading={pdfLoading}
                pdfError={pdfError}
                pdfTextContent={pdfTextContent}
                pageCount={pageCount}
                onRetryLoadPdf={handleLoadPdf}
                activePdfPage={activePdfPage}
                setActivePdfPage={setActivePdfPage}
                zoomLevel={zoomLevel}
                setZoomLevel={setZoomLevel}
                canvasRef={canvasRef}
                highlights={highlights}
                onReupload={handleReupload}
                onDelete={onRequestDeleteDocument}
              />
            )}
          </>
        )}
      </div>

      <ConfirmDialog
        isOpen={!!deleteConfirmDocId}
        title="Delete Document & Pipeline Data"
        message="Are you sure you want to permanently delete this document and all associated pipeline data? This action cannot be undone."
        confirmText="Delete Document"
        cancelText="Cancel"
        variant="danger"
        loading={deleteLoading}
        onConfirm={handleConfirmWorkspaceDelete}
        onCancel={() => setDeleteConfirmDocId(null)}
      />

      {/* ── Developer Panel (bottom drawer) ───────────────── */}
      <BottomDrawer isOpen={devPanelOpen} onClose={onToggleDevPanel} selectedPipelineId={selectedPipelineId}>
        <DeveloperPanelTabs
          activeDag={currentActiveDag}
          onRetryTask={onRetryTask}
          selectedPipelineId={selectedPipelineId}
        />
      </BottomDrawer>
    </div>
  );
};

export default WorkspaceHome;
