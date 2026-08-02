import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { usePipeline } from '../contexts/PipelineContext';
import { useDocument } from '../contexts/DocumentContext';
import { useWorkspace } from '../contexts/WorkspaceContext';
import {
  createQueryPipelineV1,
  fetchQueryPipelineAnswerV1,
} from '../services/search';
import { fetchUploadedFiles, fetchPdfContent } from '../services/documents';
import {
  fetchPipelineDetails,
} from '../services/pipelines';
import { apiClient } from '../services/apiClient';

// ── Workspace State Components ────────────────────────────────
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
  if (s === 'completed') return WS.READY;
  if (['queued', 'running', 'waiting', 'paused', 'pending', 'failed', 'cancelled'].includes(s))
    return WS.PROCESSING;
  return WS.EMPTY;
};

export const WorkspaceHome = ({ activeTab, devPanelOpen, onToggleDevPanel }) => {
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
        setUploadedFiles(files || []);
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

  // ─────────────────────────────────────────────────────────
  // Derive workspace state from selected document + pipeline
  // Automatic transitions — no manual navigation required
  // ─────────────────────────────────────────────────────────
  useEffect(() => {
    // Override: parent navigation tab forces Upload
    if (activeTab === 'upload') {
      setWorkspaceState(WS.EMPTY);
      return;
    }

    if (!selectedDocumentId) {
      setWorkspaceState(WS.EMPTY);
      return;
    }

    localStorage.setItem('scaleflow_active_doc', selectedDocumentId);

    const doc   = uploadedFiles.find((f) => f.id === selectedDocumentId);
    const assoc = pipelines.find(
      (p) => p.file_id === selectedDocumentId || (doc && (p.file_id === doc.id || p.id === doc.pipeline_id))
    );

    if (assoc) {
      setSelectedPipelineId(assoc.id);
      const nextState = pipelineStatusToWsState(assoc.status);
      setWorkspaceState(nextState);
    } else {
      // No pipeline yet — show processing (polling will pick it up shortly)
      setWorkspaceState(WS.PROCESSING);
    }
  }, [selectedDocumentId, uploadedFiles, pipelines, setSelectedPipelineId, activeTab]);

  // ─────────────────────────────────────────────────────────
  // Poll pipeline details (DAG + metadata) every 3s
  // ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (!selectedPipelineId || replayMode) return;
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
    const interval = setInterval(load, 3000);
    return () => clearInterval(interval);
  }, [selectedPipelineId, refreshTrigger, replayMode]);

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
  useEffect(() => {
    if (!selectedDocumentId || workspaceState !== WS.READY) {
      setPdfDoc(null);
      return;
    }
    const loadPdf = async () => {
      try {
        const blob        = await fetchPdfContent(selectedDocumentId);
        const arrayBuffer = await blob.arrayBuffer();
        const pdfjs       = await import('pdfjs-dist/build/pdf');
        pdfjs.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.mjs';
        const pdf = await pdfjs.getDocument({ data: arrayBuffer }).promise;
        setPdfDoc(pdf);
        setActivePdfPage(1);
      } catch (err) {
        console.error('Error loading PDF via pdfjs-dist', err);
      }
    };
    loadPdf();
  }, [selectedDocumentId, workspaceState]);

  // ─────────────────────────────────────────────────────────
  // Render canvas page
  // ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (!pdfDoc || !canvasRef.current) return;
    const renderPage = async () => {
      try {
        const page     = await pdfDoc.getPage(activePdfPage);
        const viewport = page.getViewport({ scale: zoomLevel / 100 });
        const canvas   = canvasRef.current;
        const ctx      = canvas.getContext('2d');
        canvas.height  = viewport.height;
        canvas.width   = viewport.width;
        await page.render({ canvasContext: ctx, viewport }).promise;
      } catch (err) {
        console.error('Error rendering PDF page', err);
      }
    };
    renderPage();
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
        const data = JSON.parse(event.data);
        if (data.stage === 'retrieving') setCurrentQueryStage('vector');
        else if (data.stage === 'reranking') setCurrentQueryStage('fusion');
        else if (data.stage === 'generating') setCurrentQueryStage('llm');
      });

      es.addEventListener('token', (event) => {
        const data = JSON.parse(event.data);
        accumulator += data.token;
        setChatThread((prev) =>
          prev.map((m) => (m.id === tempMsgId ? { ...m, content: accumulator, isStreaming: true } : m))
        );
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
    if (citation.page !== undefined) setActivePdfPage(citation.page);
    if (citation.bounding_box) {
      setHighlights([citation.bounding_box]);
    } else {
      setHighlights([{ x: 50, y: 80, width: 250, height: 30, page: citation.page || 1 }]);
    }
  }, []);

  // ─────────────────────────────────────────────────────────
  // Derived helpers
  // ─────────────────────────────────────────────────────────
  const activeDoc = uploadedFiles.find((f) => f.id === selectedDocumentId);

  const handleSelectDocument = (doc) => {
    setSelectedDocumentId(doc.id);
    selectDocument(doc.id);
  };

  const handleReupload = () => {
    setWorkspaceState(WS.EMPTY);
    setSelectedDocumentId(null);
    setPdfDoc(null);
    setActiveDag(null);
    setChatThread([
      {
        role: 'assistant',
        content: 'Document indexed. Ask any question to begin.',
        timestamp: new Date().toLocaleTimeString(),
      },
    ]);
  };

  const handleUploadComplete = (newDoc) => {
    // Backend returned a new document; switch to PROCESSING and select it
    if (newDoc?.id) {
      setSelectedDocumentId(newDoc.id);
    }
    setWorkspaceState(WS.PROCESSING);
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

        {workspaceState === WS.EMPTY && (
          <UploadWorkspace
            uploadedFiles={uploadedFiles}
            onSelectDocument={handleSelectDocument}
            onUploadComplete={handleUploadComplete}
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
          />
        )}

        {workspaceState === WS.READY && (
          <ReadyWorkspace
            activeDoc={activeDoc}
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
            activePdfPage={activePdfPage}
            setActivePdfPage={setActivePdfPage}
            zoomLevel={zoomLevel}
            setZoomLevel={setZoomLevel}
            canvasRef={canvasRef}
            highlights={highlights}
            onReupload={handleReupload}
          />
        )}
      </div>

      {/* ── Developer Panel (bottom drawer) ───────────────── */}
      <BottomDrawer isOpen={devPanelOpen} onClose={onToggleDevPanel}>
        <DeveloperPanelTabs
          activeDag={currentActiveDag}
          onRetryTask={onRetryTask}
        />
      </BottomDrawer>
    </div>
  );
};

export default WorkspaceHome;
