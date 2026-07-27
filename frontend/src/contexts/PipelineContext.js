import React, { createContext, useState, useContext, useEffect, useRef } from 'react';
import { fetchPipelineTimeline, retryTask } from '../services/pipelines';

const PipelineContext = createContext(null);

const SEVERITY_MAP = {
  "task_failed":                   "ERROR",
  "pipeline_failed":               "ERROR",
  "task_blocked":                  "WARNING",
  "task_recovered":                "WARNING",
  "lease_expired":                 "WARNING",
  "backpressure_deferred":         "WARNING",
  "dependency_blocked":            "WARNING",
  "stale_worker_update_rejected":  "WARNING",
  "queue_pressure_update":         "WARNING",
  "priority_escalated":            "WARNING",
  "pipeline_ownership_taken_over": "WARNING",
};

export const normalizeTimelineEvent = (e) => {
  const level = SEVERITY_MAP[e.event_type] ?? "INFO";

  const rawTimestamp = e.created_at || null;
  let displayTime = "Not Available";
  if (rawTimestamp) {
    try {
      displayTime = new Date(rawTimestamp).toLocaleTimeString([], {
        hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit'
      });
    } catch (_) {}
  }

  const taskId = e.task_id ?? null;
  const taskType = e.task_type || "unknown";

  return {
    id:           e.id,
    event_type:   e.event_type  || "unknown",
    task_id:      taskId,
    task_type:    taskType,
    message:      e.message     || "Not Available",
    worker_id:    e.worker_id   || "system",
    pipeline_id:  e.pipeline_id ?? "Not Available",
    level,
    rawTimestamp,
    displayTime,
  };
};

const mergeEvents = (prev, raw) => {
  const normalized = raw.map(normalizeTimelineEvent);
  const existingIds = new Set(prev.map(e => e.id));
  const newEntries = normalized.filter(e => e.id !== undefined && e.id !== null && !existingIds.has(e.id));
  if (newEntries.length === 0) return prev;
  const combined = [...prev, ...newEntries];
  combined.sort((a, b) => {
    const tA = a.rawTimestamp ? new Date(a.rawTimestamp).getTime() : Infinity;
    const tB = b.rawTimestamp ? new Date(b.rawTimestamp).getTime() : Infinity;
    return tA - tB;
  });
  return combined.slice(-1000);
};

export const PipelineProvider = ({ children }) => {
  const [selectedPipelineId, setSelectedPipelineId] = useState(null);
  const [pipelines, setPipelines] = useState([]);
  const [selectedTaskId, setSelectedTaskId] = useState(null);
  const [testing, setTesting] = useState(false);
  const [showTestModal, setShowTestModal] = useState(false);
  const [testResults, setTestResults] = useState(null);

  const [timelineEvents, setTimelineEvents] = useState([]);
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [timelineError, setTimelineError] = useState(null);

  const abortRef = useRef(null);
  const intervalRef = useRef(null);

  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const onRetryTask = async (taskId, force = false) => {
    await retryTask(taskId, force);
    // Invalidate pipeline cache and trigger a coordinated refresh cycle
    setRefreshTrigger(prev => prev + 1);
  };

  useEffect(() => {
    if (abortRef.current) abortRef.current.abort();
    clearInterval(intervalRef.current);

    if (!selectedPipelineId) {
      setTimelineEvents([]);
      setTimelineError(null);
      setTimelineLoading(false);
      return;
    }

    // Preserve log events on minor refreshes, only reset completely on selectedPipelineId changes
    setTimelineLoading(true);

    const poll = async () => {
      const controller = new AbortController();
      abortRef.current = controller;
      try {
        const raw = await fetchPipelineTimeline(selectedPipelineId, controller.signal);
        if (controller.signal.aborted) return;
        setTimelineEvents(prev => mergeEvents(prev, raw || []));
        setTimelineError(null);
      } catch (err) {
        if (err.name === 'CanceledError' || err.name === 'AbortError') return;
        setTimelineError(err.message ?? 'Failed to load timeline');
      } finally {
        if (!controller.signal.aborted) setTimelineLoading(false);
      }
    };

    poll();
    intervalRef.current = setInterval(poll, 2500);

    return () => {
      abortRef.current?.abort();
      clearInterval(intervalRef.current);
    };
  }, [selectedPipelineId, refreshTrigger]);

  return (
    <PipelineContext.Provider value={{
      selectedPipelineId,
      setSelectedPipelineId,
      pipelines,
      setPipelines,
      selectedTaskId,
      setSelectedTaskId,
      testing,
      setTesting,
      showTestModal,
      setShowTestModal,
      testResults,
      setTestResults,
      timelineEvents,
      timelineLoading,
      timelineError,
      refreshTrigger,
      onRetryTask
    }}>
      {children}
    </PipelineContext.Provider>
  );
};

export const usePipeline = () => {
  const context = useContext(PipelineContext);
  if (!context) {
    throw new Error('usePipeline must be used within a PipelineProvider');
  }
  return context;
};
