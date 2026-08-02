import React, { useEffect, useRef } from 'react';
import { UploadCloud, AlertTriangle } from 'lucide-react';
import { PipelineHeader } from './PipelineHeader';
import { PipelineControls } from './PipelineControls';
import { ExecutionConsole } from '../logs/ExecutionConsole';
import { ErrorPanel } from '../logs/ErrorPanel';
import PipelineStepper from '../../layout/PipelineStepper';
import { cancelPipeline, retryPipeline } from '../../../services/pipelines';

/* ─────────────────────────────────────────────────────────────
 *  WORKSPACE_PROCESSING — Pipeline Monitoring State
 *
 *  Renders ONLY pipeline execution information.
 *  Chat, PDF Viewer, Retrieval Inspector, Graph Explorer
 *  are completely hidden in this state.
 *
 *  Guard: If no pipeline is present, shows "No active pipeline"
 *  empty state with a CTA to go back to upload.
 * ───────────────────────────────────────────────────────────── */

/** Maps backend task_type to a human-readable stepper step label */
const STAGE_LABELS = [
  { key: 'upload',      label: 'Upload'       },
  { key: 'ocr',         label: 'OCR / VLM'    },
  { key: 'layout',      label: 'Layout Graph' },
  { key: 'chunking',    label: 'Chunking'     },
  { key: 'embedding',   label: 'Embedding'    },
  { key: 'indexing',    label: 'Indexing'     },
  { key: 'ready',       label: 'Ready'        },
];

/** Derive active step index from current task list */
const resolveActiveStep = (tasks = []) => {
  const keyOrder = STAGE_LABELS.map((s) => s.key);
  let activeIdx = 0;
  tasks.forEach((t) => {
    const normalizedType = (t.type || t.task_type || '').toLowerCase();
    const match = keyOrder.findIndex((k) => normalizedType.includes(k));
    if (match >= 0) {
      if (t.status === 'running') activeIdx = match;
      else if (t.status === 'completed') activeIdx = Math.max(activeIdx, match + 1);
    }
  });
  return Math.min(activeIdx, STAGE_LABELS.length - 1);
};

export const ProcessingWorkspace = ({
  /** Object from fetchPipelineDetails — { pipeline: {...}, tasks: [...], artifacts: [...] } */
  activeDag,
  selectedPipelineId,
  /** The document currently being processed */
  activeDoc,
  /** Timeline events from PipelineContext */
  timelineEvents,
  timelineLoading,
  timelineError,
  onRetryTask,
  /** Callback: user clicked "Re-upload" */
  onReupload,
}) => {
  const logEndRef = useRef(null);

  // Scroll logs to bottom when new events arrive
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [timelineEvents]);

  /* ── Guard: no pipeline ───────────────────────────────────── */
  if (!activeDag || !activeDag.pipeline) {
    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          gap: '20px',
          padding: '64px 24px',
        }}
      >
        <div
          style={{
            width: 72,
            height: 72,
            borderRadius: '50%',
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.08)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <AlertTriangle size={28} style={{ color: 'rgba(255,255,255,0.25)' }} />
        </div>
        <div style={{ textAlign: 'center' }}>
          <div
            style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: 6 }}
          >
            No active pipeline
          </div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Upload a PDF to begin processing.
          </div>
        </div>
        <button
          onClick={onReupload}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            background: 'rgba(59,130,246,0.08)',
            border: '1px solid rgba(59,130,246,0.2)',
            borderRadius: 8,
            color: '#3b82f6',
            padding: '10px 20px',
            fontSize: '0.85rem',
            fontWeight: 600,
            cursor: 'pointer',
            transition: 'all 0.2s',
          }}
        >
          <UploadCloud size={16} />
          Upload PDF
        </button>
      </div>
    );
  }

  const { pipeline, tasks = [] } = activeDag;
  const activeStepIdx = resolveActiveStep(tasks);

  // Derive errors from failed tasks
  const errorItems = tasks
    .filter((t) => t.status === 'failed' || t.status === 'cancelled')
    .map((t) => {
      const sortTimestamp = t.completed_at || t.updated_at || t.created_at || '';
      return {
        id: t.id,
        level: 'error',
        status: t.status,
        message: t.error_message || `${t.type || t.task_type} stage failed`,
        stage: t.type || t.task_type || 'Unknown',
        worker: t.assigned_worker_id ?? 'Not Available',
        retries: t.retry_count ?? 0,
        maxRetries: t.max_retries ?? 3,
        queueWait: t.queue_wait_duration ?? 'N/A',
        executionDuration: t.execution_duration ?? 'N/A',
        timestamp: sortTimestamp ? new Date(sortTimestamp).toLocaleString() : 'N/A',
        sortTimestamp: sortTimestamp ? new Date(sortTimestamp).getTime() : 0,
      };
    })
    .sort((a, b) => b.sortTimestamp - a.sortTimestamp);

  const elapsedSeconds = pipeline.started_at
    ? Math.round(
        (new Date(pipeline.completed_at || new Date().toISOString()) -
          new Date(pipeline.started_at)) /
          1000
      )
    : 0;

  const activeWorker =
    tasks.find((t) => t.status === 'running')?.assigned_worker_id || null;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '0',
        height: '100%',
        overflowY: 'auto',
      }}
    >
      {/* ── Section: Pipeline Header ─────────────────────────── */}
      <div
        style={{
          padding: '24px 32px 20px',
          borderBottom: '1px solid var(--border-subtle)',
          background: 'var(--bg-panel)',
          position: 'sticky',
          top: 0,
          zIndex: 10,
        }}
      >
        <PipelineHeader
          pipelineId={selectedPipelineId}
          documentName={activeDoc?.original_filename}
          workerId={activeWorker || 'Unassigned'}
          status={pipeline.status}
          elapsedSeconds={elapsedSeconds}
          queuePosition={tasks.find((t) => t.status === 'pending')?.queue_position || null}
          startTime={pipeline.started_at}
        />
      </div>

      {/* ── Section: Pipeline Stepper ────────────────────────── */}
      <div
        style={{
          padding: '24px 32px',
          borderBottom: '1px solid var(--border-subtle)',
          background: 'var(--bg-primary)',
        }}
      >
        <div
          style={{
            fontSize: '11px',
            fontWeight: 700,
            color: 'rgba(255,255,255,0.3)',
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            marginBottom: '16px',
          }}
        >
          Pipeline Progress
        </div>
        <PipelineStepper
          steps={STAGE_LABELS.map((s) => s.label)}
          activeStep={activeStepIdx}
        />
      </div>

      {/* ── Section: Runtime Summary + Controls ─────────────── */}
      <div
        style={{
          padding: '20px 32px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          flexWrap: 'wrap',
          gap: '24px',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
        }}
      >
        {/* Runtime metrics grid */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
            gap: '16px',
            flex: 1,
            minWidth: 0,
          }}
        >
          {[
            ['Started', pipeline.started_at ? new Date(pipeline.started_at).toLocaleTimeString() : 'Pending'],
            ['Current Runtime', elapsedSeconds ? `${elapsedSeconds}s` : '—'],
            ['Current Worker', activeWorker || 'Unassigned'],
            ['Queue Position', tasks.find((t) => t.status === 'pending')?.queue_position ?? '—'],
            ['Current Stage', STAGE_LABELS[activeStepIdx]?.label || '—'],
            ['Total Tasks', tasks.length || '—'],
          ].map(([label, value]) => (
            <div key={label}>
              <div
                style={{
                  fontSize: '10px',
                  color: 'rgba(255,255,255,0.3)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                  fontWeight: 700,
                  marginBottom: '4px',
                }}
              >
                {label}
              </div>
              <div
                style={{
                  fontSize: '0.88rem',
                  color: 'var(--text-primary)',
                  fontWeight: 600,
                  fontFamily: 'var(--font-mono)',
                }}
              >
                {value}
              </div>
            </div>
          ))}
        </div>

        {/* Pipeline controls */}
        <div style={{ flexShrink: 0 }}>
          <PipelineControls
            status={pipeline.status}
            onPause={null}
            onResume={null}
            onCancel={async () => {
              try { await cancelPipeline(selectedPipelineId); } catch (e) { console.error('cancel failed', e); }
            }}
            onRetry={async () => {
              try { await retryPipeline(selectedPipelineId); } catch (e) { console.error('retry failed', e); }
            }}
            onReupload={onReupload}
            onDelete={null}
          />
        </div>
      </div>

      {/* ── Section: Stage Progress Table ───────────────────── */}
      <div
        style={{
          padding: '20px 32px',
          borderBottom: '1px solid var(--border-subtle)',
        }}
      >
        <div
          style={{
            fontSize: '11px',
            fontWeight: 700,
            color: 'rgba(255,255,255,0.3)',
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            marginBottom: '12px',
          }}
        >
          Stage Progress
        </div>
        <div
          style={{
            border: '1px solid var(--border-subtle)',
            borderRadius: '8px',
            overflow: 'hidden',
          }}
        >
          {/* Table header */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '2fr 1fr 1.2fr 1.2fr 1fr 1.2fr 0.7fr',
              gap: '0',
              background: 'rgba(255,255,255,0.02)',
              borderBottom: '1px solid var(--border-subtle)',
              padding: '8px 16px',
              fontSize: '10px',
              color: 'rgba(255,255,255,0.35)',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              fontFamily: 'var(--font-mono)',
            }}
          >
            {['Stage', 'Status', 'Started', 'Finished', 'Duration', 'Worker', 'Retries'].map(
              (col) => <span key={col}>{col}</span>
            )}
          </div>

          {/* Table rows */}
          {tasks.length > 0 ? (
            tasks.map((task) => {
              const statusColor =
                task.status === 'completed'
                  ? 'var(--color-success)'
                  : task.status === 'failed'
                  ? 'var(--color-failure)'
                  : task.status === 'running'
                  ? 'var(--color-pipeline-running, #6366f1)'
                  : 'var(--text-muted)';
              return (
                <div
                  key={task.id}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '2fr 1fr 1.2fr 1.2fr 1fr 1.2fr 0.7fr',
                    gap: '0',
                    padding: '10px 16px',
                    borderBottom: '1px solid rgba(255,255,255,0.03)',
                    fontSize: '12px',
                    fontFamily: 'var(--font-mono)',
                    alignItems: 'center',
                    minHeight: '40px',
                  }}
                >
                  <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
                    {task.type || task.task_type || '—'}
                  </span>
                  <span style={{ color: statusColor, fontWeight: 700, textTransform: 'uppercase', fontSize: '10px' }}>
                    {task.status}
                  </span>
                  <span style={{ color: 'var(--text-secondary)' }}>
                    {task.started_at ? new Date(task.started_at).toLocaleTimeString() : '—'}
                  </span>
                  <span style={{ color: 'var(--text-secondary)' }}>
                    {task.completed_at ? new Date(task.completed_at).toLocaleTimeString() : '—'}
                  </span>
                  <span style={{ color: 'var(--text-secondary)' }}>
                    {task.execution_duration != null ? `${task.execution_duration}s` : '—'}
                  </span>
                  <span style={{ color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {task.assigned_worker_id || '—'}
                  </span>
                  <span style={{ color: task.retry_count > 0 ? 'var(--color-warning)' : 'var(--text-muted)' }}>
                    {task.retry_count ?? 0}
                  </span>
                </div>
              );
            })
          ) : (
            <div
              style={{
                padding: '24px',
                textAlign: 'center',
                fontSize: '12px',
                color: 'var(--text-disabled)',
                fontFamily: 'var(--font-mono)',
              }}
            >
              Awaiting task data from backend...
            </div>
          )}
        </div>
      </div>

      {/* ── Section: Execution Log ───────────────────────────── */}
      <div
        style={{
          padding: '20px 32px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
        }}
      >
        <div
          style={{
            fontSize: '11px',
            fontWeight: 700,
            color: 'rgba(255,255,255,0.3)',
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
          }}
        >
          Execution Log
        </div>
        <div style={{ maxHeight: '220px', overflow: 'hidden', borderRadius: '8px' }}>
          <ExecutionConsole
            events={timelineEvents}
            loading={timelineLoading}
            error={timelineError}
          />
        </div>
        <div ref={logEndRef} />
      </div>

      {/* ── Section: Error Panel (only when errors exist) ───── */}
      {errorItems.length > 0 ? (
        <div style={{ padding: '20px 32px' }}>
          <div
            style={{
              fontSize: '11px',
              fontWeight: 700,
              color: 'var(--color-failure)',
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              marginBottom: '12px',
            }}
          >
            Errors ({errorItems.length})
          </div>
          <ErrorPanel errors={errorItems} onRetryTask={onRetryTask} />
        </div>
      ) : (
        <div
          style={{
            padding: '20px 32px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
          }}
        >
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: 'var(--color-success)',
            }}
          />
          <span
            style={{
              fontSize: '12px',
              color: 'var(--text-muted)',
              fontFamily: 'var(--font-mono)',
            }}
          >
            No errors detected.
          </span>
        </div>
      )}
    </div>
  );
};

export default ProcessingWorkspace;
