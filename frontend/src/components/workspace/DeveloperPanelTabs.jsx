import React, { useState } from 'react';
import { usePipeline } from '../../contexts/PipelineContext';
import { useDocument } from '../../contexts/DocumentContext';
import { ExecutionConsole } from './logs/ExecutionConsole';
import { ErrorPanel } from './logs/ErrorPanel';
import { PipelineDAG } from './pipeline/PipelineDAG';
import { PerformanceTimeline } from './timeline/PerformanceTimeline';
import { FlameGraph } from './timeline/FlameGraph';
import { WorkerUtilizationChart } from './timeline/WorkerUtilizationChart';
import { StageBreakdown } from './timeline/StageBreakdown';
import { OptimizationTab } from './timeline/OptimizationTab';
import { ForecastTab } from './timeline/ForecastTab';
import { SchedulingAdvisorTab } from './timeline/SchedulingAdvisorTab';
import { RetrievalInspector } from '../../pages/RetrievalInspector';
import { GraphExplorer } from './documents/GraphExplorer';

/**
 * DeveloperPanelTabs
 *
 * All advanced developer/diagnostic tools in a single tabbed component.
 * This is rendered inside the BottomDrawer and is the ONLY location
 * for infrastructure details, telemetry, retrieval internals, and graphs.
 *
 * Tabs are ordered by estimated frequency of use:
 * 1. Logs
 * 2. Errors
 * 3. Replay (DAG)
 * 4. Performance
 * 5. Retrieval
 * 6. Graph
 * 7. Optimization
 * 8. Forecast
 * 9. Scheduling
 * 10. Telemetry
 * 11. Infrastructure
 */

const TABS = [
  { id: 'logs',           label: 'Logs'           },
  { id: 'errors',         label: 'Errors'         },
  { id: 'replay',         label: 'Replay'         },
  { id: 'performance',    label: 'Performance'    },
  { id: 'retrieval',      label: 'Retrieval'      },
  { id: 'graph',          label: 'Graph'          },
  { id: 'optimization',   label: 'Optimization'   },
  { id: 'forecast',       label: 'Forecast'       },
  { id: 'scheduling',     label: 'Scheduling'     },
  { id: 'telemetry',      label: 'Telemetry'      },
  { id: 'infrastructure', label: 'Infrastructure' },
];

export const DeveloperPanelTabs = ({ activeDag, onRetryTask }) => {
  const [activeTab, setActiveTab] = useState('logs');

  const {
    selectedPipelineId,
    timelineEvents, timelineLoading, timelineError,
    performanceModel, performanceLoading, performanceError,
    optimizationModel, optimizationLoading, optimizationError,
  } = usePipeline();

  const { selectedDocumentId } = useDocument();

  // Derive errors from failed tasks
  const errorItems = (activeDag?.tasks || [])
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

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>

      {/* ── Tab Bar ──────────────────────────────────────────── */}
      <div
        style={{
          display: 'flex',
          overflowX: 'auto',
          gap: '2px',
          borderBottom: '1px solid var(--border-subtle)',
          background: 'var(--bg-panel)',
          flexShrink: 0,
          padding: '0 16px',
          scrollbarWidth: 'none',
        }}
      >
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              background: 'none',
              border: 'none',
              borderBottom: activeTab === tab.id
                ? '2px solid var(--color-accent)'
                : '2px solid transparent',
              color: activeTab === tab.id
                ? 'var(--text-primary)'
                : 'var(--text-muted)',
              padding: '8px 14px',
              fontSize: '11px',
              fontWeight: 600,
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              transition: 'color 0.15s, border-color 0.15s',
              flexShrink: 0,
            }}
            onMouseEnter={(e) => {
              if (activeTab !== tab.id)
                e.currentTarget.style.color = 'var(--text-secondary)';
            }}
            onMouseLeave={(e) => {
              if (activeTab !== tab.id)
                e.currentTarget.style.color = 'var(--text-muted)';
            }}
          >
            {tab.label}
            {tab.id === 'errors' && errorItems.length > 0 && (
              <span
                style={{
                  marginLeft: 5,
                  background: 'var(--color-failure)',
                  color: '#fff',
                  borderRadius: 10,
                  padding: '1px 6px',
                  fontSize: '9px',
                  fontWeight: 700,
                  verticalAlign: 'middle',
                }}
              >
                {errorItems.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* ── Tab Content ──────────────────────────────────────── */}
      <div style={{ flex: 1, overflow: 'auto', padding: '16px' }}>

        {/* LOGS */}
        {activeTab === 'logs' && (
          <ExecutionConsole
            events={timelineEvents}
            loading={timelineLoading}
            error={timelineError}
          />
        )}

        {/* ERRORS */}
        {activeTab === 'errors' && (
          errorItems.length > 0 ? (
            <ErrorPanel errors={errorItems} onRetryTask={onRetryTask} />
          ) : (
            <EmptyTabState message="No errors detected." />
          )
        )}

        {/* REPLAY (Pipeline DAG) */}
        {activeTab === 'replay' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <SectionLabel>Pipeline Visual DAG</SectionLabel>
            <PipelineDAG
              tasks={activeDag?.tasks || []}
              artifacts={activeDag?.artifacts || []}
            />
            <SectionLabel>Pipeline Task Stages</SectionLabel>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {(activeDag?.tasks || []).length > 0 ? (
                activeDag.tasks.map((task, idx) => (
                  <span
                    key={idx}
                    style={{
                      padding: '4px 10px',
                      borderRadius: 6,
                      fontSize: '11px',
                      fontFamily: 'var(--font-mono)',
                      fontWeight: 600,
                      background:
                        task.status === 'completed'
                          ? 'rgba(16,185,129,0.1)'
                          : task.status === 'failed'
                          ? 'rgba(244,63,94,0.1)'
                          : 'rgba(245,158,11,0.1)',
                      color:
                        task.status === 'completed'
                          ? 'var(--color-success)'
                          : task.status === 'failed'
                          ? 'var(--color-failure)'
                          : 'var(--color-warning)',
                      border: '1px solid currentColor',
                    }}
                  >
                    {task.task_type || task.type}: {task.status}
                  </span>
                ))
              ) : (
                <EmptyTabState message={selectedPipelineId ? 'Awaiting backend task data...' : 'No active pipeline'} />
              )}
            </div>
          </div>
        )}

        {/* PERFORMANCE */}
        {activeTab === 'performance' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <SectionLabel>Performance Analytics</SectionLabel>
            {performanceLoading && <LoadingNote label="Analyzing execution latency..." />}
            {performanceError && <ErrorNote message={performanceError} />}
            {!performanceLoading && !performanceError && performanceModel ? (
              <>
                <PerformanceTimeline />
                <FlameGraph />
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
                  <WorkerUtilizationChart workers={performanceModel.performance?.workers} />
                  <StageBreakdown stages={performanceModel.performance?.stages} />
                </div>
              </>
            ) : (
              !performanceLoading && !performanceError && (
                <EmptyTabState message="Run a pipeline in replay mode to view performance analytics." />
              )
            )}
          </div>
        )}

        {/* RETRIEVAL */}
        {activeTab === 'retrieval' && (
          selectedDocumentId ? (
            <RetrievalInspector />
          ) : (
            <EmptyTabState message="Select a document to inspect retrieval." />
          )
        )}

        {/* GRAPH */}
        {activeTab === 'graph' && (
          selectedDocumentId ? (
            <GraphExplorer />
          ) : (
            <EmptyTabState message="Select a document to explore the graph." />
          )
        )}

        {/* OPTIMIZATION */}
        {activeTab === 'optimization' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <SectionLabel>Performance Recommendations & Simulation</SectionLabel>
            <OptimizationTab
              optimizationModel={optimizationModel}
              loading={optimizationLoading}
              error={optimizationError}
            />
          </div>
        )}

        {/* FORECAST */}
        {activeTab === 'forecast' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <SectionLabel>Predictive Execution Forecasting</SectionLabel>
            <ForecastTab />
          </div>
        )}

        {/* SCHEDULING */}
        {activeTab === 'scheduling' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <SectionLabel>Adaptive Scheduling Advisor</SectionLabel>
            <SchedulingAdvisorTab />
          </div>
        )}

        {/* TELEMETRY */}
        {activeTab === 'telemetry' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <SectionLabel>Trace & Telemetry</SectionLabel>
            {activeDag?.tasks?.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {activeDag.tasks.map((t, i) => (
                  <div
                    key={i}
                    style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
                      gap: 12,
                      padding: '10px 14px',
                      background: 'rgba(255,255,255,0.02)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 8,
                      fontSize: '11px',
                      fontFamily: 'var(--font-mono)',
                    }}
                  >
                    <MetricRow label="Stage" value={t.type || t.task_type || '—'} />
                    <MetricRow label="Worker" value={t.assigned_worker_id || '—'} />
                    <MetricRow label="Queue Wait" value={t.queue_wait_duration != null ? `${t.queue_wait_duration}s` : '—'} />
                    <MetricRow label="Exec Duration" value={t.execution_duration != null ? `${t.execution_duration}s` : '—'} />
                    <MetricRow label="Retries" value={t.retry_count ?? 0} />
                    <MetricRow label="Status" value={t.status} />
                  </div>
                ))}
              </div>
            ) : (
              <EmptyTabState message="No telemetry data available." />
            )}
          </div>
        )}

        {/* INFRASTRUCTURE */}
        {activeTab === 'infrastructure' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <SectionLabel>Infrastructure Health</SectionLabel>
            <div
              style={{
                padding: '24px',
                background: 'rgba(255,255,255,0.02)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 8,
                fontSize: '12px',
                color: 'var(--text-muted)',
                textAlign: 'center',
              }}
            >
              Infrastructure metrics are available on the Infrastructure page (Dev Mode).
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

/* ── Small helper components ──────────────────────────────── */

const SectionLabel = ({ children }) => (
  <div
    style={{
      fontSize: '10px',
      fontWeight: 700,
      color: 'rgba(255,255,255,0.3)',
      textTransform: 'uppercase',
      letterSpacing: '0.08em',
      marginBottom: '4px',
    }}
  >
    {children}
  </div>
);

const EmptyTabState = ({ message }) => (
  <div
    style={{
      padding: '40px',
      textAlign: 'center',
      fontSize: '12px',
      color: 'var(--text-disabled)',
      fontFamily: 'var(--font-mono)',
    }}
  >
    {message}
  </div>
);

const LoadingNote = ({ label }) => (
  <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
    {label}
  </div>
);

const ErrorNote = ({ message }) => (
  <div style={{ fontSize: '12px', color: 'var(--color-failure)', fontFamily: 'var(--font-mono)' }}>
    {message}
  </div>
);

const MetricRow = ({ label, value }) => (
  <div>
    <div style={{ color: 'rgba(255,255,255,0.3)', fontSize: '9px', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 2 }}>
      {label}
    </div>
    <div style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{String(value)}</div>
  </div>
);

export default DeveloperPanelTabs;
