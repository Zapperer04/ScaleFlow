import React, { createContext, useState, useContext, useEffect, useRef } from 'react';
import { fetchPipelineTimeline, retryTask, fetchPipelineReplay } from '../services/pipelines';

const PipelineContext = createContext(null);

export const normalizeReplayEvent = (e) => {
  const level = SEVERITY_MAP[e.event_type] ?? "INFO";

  const rawTimestamp = e.timestamp || e.created_at || null;
  let displayTime = "Not Available";
  if (rawTimestamp) {
    try {
      displayTime = new Date(rawTimestamp).toLocaleTimeString([], {
        hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit'
      });
    } catch (_) {}
  }

  return {
    id:             e.id || Math.random().toString(),
    source:         e.source || "task_log",
    event_type:     e.event_type || "unknown",
    task_id:        e.task_id ?? null,
    task_type:      e.task_type || "unknown",
    message:        e.message || "Not Available",
    worker_id:      e.worker_id || "system",
    pipeline_id:    e.pipeline_id ?? "Not Available",
    correlation_id: e.correlation_id ?? null,
    status_before:  e.status_before || null,
    status_after:   e.status_after || null,
    payload:        e.payload || {},
    level,
    rawTimestamp,
    displayTime,
  };
};

export const computeReplaySnapshots = (events) => {
  const snapshots = [];
  let currentTasks = {};
  let currentWorkers = {};
  let selectedTaskId = null;
  let selectedWorkerId = null;
  let selectedTraceId = null;

  for (let i = 0; i < events.length; i++) {
    const e = events[i];
    
    // We update task states if this event relates to a task
    let nextTasks = currentTasks;
    if (e.task_id) {
      const taskId = String(e.task_id);
      const prevTask = currentTasks[taskId] || {
        status: 'pending',
        workerId: null,
        retryCount: 0,
        queue: null,
        progress: null
      };

      // Determine updated status/fields
      let nextStatus = prevTask.status;
      if (e.status_after) {
        nextStatus = e.status_after;
      } else if (e.event_type === 'task_blocked' || e.event_type === 'dependency_blocked') {
        nextStatus = 'blocked';
      } else if (e.event_type === 'task_retry' || e.event_type === 'task_recovered') {
        nextStatus = 'retrying';
      }

      let nextWorkerId = prevTask.workerId;
      if (e.worker_id && e.worker_id !== 'system') {
        nextWorkerId = e.worker_id;
      }

      let nextRetryCount = prevTask.retryCount;
      if (e.event_type === 'task_retry' || e.event_type === 'task_recovered' || (e.message && e.message.toLowerCase().includes('retry'))) {
        nextRetryCount = prevTask.retryCount + 1;
      }

      const nextTask = {
        ...prevTask,
        status: nextStatus,
        workerId: nextWorkerId,
        retryCount: nextRetryCount
      };

      if (JSON.stringify(prevTask) !== JSON.stringify(nextTask)) {
        nextTasks = { ...currentTasks, [taskId]: nextTask };
      }
    }

    // We update worker states if this event relates to a worker
    let nextWorkers = currentWorkers;
    if (e.worker_id && e.worker_id !== 'system') {
      const wId = e.worker_id;
      const prevWorker = currentWorkers[wId] || {
        currentTask: null,
        state: 'idle',
        leaseStatus: 'valid'
      };

      let nextState = prevWorker.state;
      let nextCurrentTask = prevWorker.currentTask;
      if (e.status_after === 'running' || e.event_type === 'task_running' || e.event_type === 'running') {
        nextState = 'busy';
        nextCurrentTask = e.task_id ? String(e.task_id) : null;
      } else if (e.status_after === 'completed' || e.status_after === 'failed' || e.event_type === 'task_completed' || e.event_type === 'task_failed') {
        nextState = 'idle';
        nextCurrentTask = null;
      }

      let nextLeaseStatus = prevWorker.leaseStatus;
      if (e.event_type === 'lease_expired') {
        nextLeaseStatus = 'expired';
        nextState = 'offline';
      }

      const nextWorker = {
        ...prevWorker,
        state: nextState,
        currentTask: nextCurrentTask,
        leaseStatus: nextLeaseStatus
      };

      if (JSON.stringify(prevWorker) !== JSON.stringify(nextWorker)) {
        nextWorkers = { ...currentWorkers, [wId]: nextWorker };
      }
    }

    // Keep active selections updated
    if (e.task_id) {
      selectedTaskId = e.task_id;
    }
    if (e.worker_id && e.worker_id !== 'system') {
      selectedWorkerId = e.worker_id;
    }
    if (e.correlation_id) {
      selectedTraceId = e.correlation_id;
    }

    // Commit current reference to state
    currentTasks = nextTasks;
    currentWorkers = nextWorkers;

    // Freeze snapshot
    const snapshot = {
      timestamp: e.timestamp,
      taskStates: currentTasks,
      workerStates: currentWorkers,
      selectedTaskId,
      selectedWorkerId,
      selectedTraceId
    };
    snapshots.push(snapshot);
  }

  return snapshots;
};

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
    source:       e.source || "task_log",
    event_type:   e.event_type  || "unknown",
    task_id:      taskId,
    task_type:    taskType,
    message:      e.message     || "Not Available",
    worker_id:    e.worker_id   || "system",
    pipeline_id:  e.pipeline_id ?? "Not Available",
    correlation_id: e.correlation_id ?? null,
    level,
    rawTimestamp,
    displayTime,
  };
};

const mergeEvents = (prev, raw) => {
  const normalized = raw.map(normalizeTimelineEvent);
  const existingKeys = new Set(prev.map(e => `${e.source}-${e.id}`));
  const newEntries = normalized.filter(e => e.id !== undefined && e.id !== null && !existingKeys.has(`${e.source}-${e.id}`));
  if (newEntries.length === 0) return prev;
  const combined = [...prev, ...newEntries];
  combined.sort((a, b) => {
    const tA = a.rawTimestamp ? new Date(a.rawTimestamp).getTime() : Infinity;
    const tB = b.rawTimestamp ? new Date(b.rawTimestamp).getTime() : Infinity;
    return tA - tB;
  });
  return combined.slice(-1000);
};

const SPEED_DELAYS = {
  0.5: 2000,
  1: 1000,
  2: 500,
  5: 200
};

export const PipelineProvider = ({ children }) => {
  const [selectedPipelineId, setSelectedPipelineId] = useState(null);
  const [pipelines, setPipelines] = useState([]);
  const [selectedTaskId, setSelectedTaskId] = useState(null);
  const [selectedTraceId, setSelectedTraceId] = useState(null);
  const [selectedWorkerId, setSelectedWorkerId] = useState(null);
  const [testing, setTesting] = useState(false);
  const [showTestModal, setShowTestModal] = useState(false);
  const [testResults, setTestResults] = useState(null);

  const [timelineEvents, setTimelineEvents] = useState([]);
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [timelineError, setTimelineError] = useState(null);

  // Replay Mode State Hooks
  const [replayMode, setReplayMode] = useState(false);
  const [replayEvents, setReplayEvents] = useState([]);
  const [replayIndex, setReplayIndex] = useState(-1);
  const [replaySnapshots, setReplaySnapshots] = useState([]);
  const [replayPlaying, setReplayPlaying] = useState(false);
  const [replaySpeed, setReplaySpeed] = useState(1); // 0.5, 1, 2, 5
  const [replayAnalysis, setReplayAnalysis] = useState(null);
  const [replayError, setReplayError] = useState(null);
  const [replayLoading, setReplayLoading] = useState(false);

  const abortRef = useRef(null);
  const intervalRef = useRef(null);
  const replayTimerRef = useRef(null);
  const abortReplayFetchRef = useRef(null);

  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const onRetryTask = async (taskId, force = false) => {
    await retryTask(taskId, force);
    setRefreshTrigger(prev => prev + 1);
  };

  // Clear active selections when selectedPipelineId changes
  useEffect(() => {
    setSelectedTaskId(null);
    setSelectedTraceId(null);
    setSelectedWorkerId(null);
  }, [selectedPipelineId]);

  // Playback Timer Loop
  useEffect(() => {
    if (replayPlaying && replayEvents.length > 0) {
      const delay = SPEED_DELAYS[replaySpeed] || 1000;
      const playNext = () => {
        setReplayIndex((prev) => {
          if (prev >= replayEvents.length - 1) {
            setReplayPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      };
      replayTimerRef.current = setTimeout(playNext, delay);
    }
    return () => {
      if (replayTimerRef.current) {
        clearTimeout(replayTimerRef.current);
        replayTimerRef.current = null;
      }
    };
  }, [replayPlaying, replayIndex, replayEvents, replaySpeed]);

  // Pipeline Switch Cleanup
  useEffect(() => {
    setReplayPlaying(false);
    if (replayTimerRef.current) {
      clearTimeout(replayTimerRef.current);
      replayTimerRef.current = null;
    }
    if (abortReplayFetchRef.current) {
      abortReplayFetchRef.current.abort();
    }
    setReplayMode(false);
    setReplayEvents([]);
    setReplaySnapshots([]);
    setReplayIndex(-1);
    setReplayAnalysis(null);
    setReplayError(null);
  }, [selectedPipelineId]);

  // Playback Control Actions
  const startReplay = () => {
    if (replayIndex >= replayEvents.length - 1) {
      setReplayIndex(0);
    }
    setReplayPlaying(true);
  };

  const pauseReplay = () => {
    setReplayPlaying(false);
  };

  const seekReplay = (idx) => {
    setReplayPlaying(false);
    if (replayTimerRef.current) {
      clearTimeout(replayTimerRef.current);
      replayTimerRef.current = null;
    }
    setReplayIndex(idx);
  };

  const stepForwardReplay = () => {
    setReplayPlaying(false);
    setReplayIndex(prev => Math.min(prev + 1, replayEvents.length - 1));
  };

  const stepBackwardReplay = () => {
    setReplayPlaying(false);
    setReplayIndex(prev => Math.max(prev - 1, 0));
  };

  const restartReplay = () => {
    setReplayPlaying(false);
    setReplayIndex(0);
  };

  const enterReplayMode = async () => {
    if (!selectedPipelineId) return;
    if (abortReplayFetchRef.current) {
      abortReplayFetchRef.current.abort();
    }
    const controller = new AbortController();
    abortReplayFetchRef.current = controller;

    setReplayLoading(true);
    setReplayError(null);
    try {
      const data = await fetchPipelineReplay(selectedPipelineId, controller.signal);
      if (controller.signal.aborted) return;

      const normalized = (data.events || []).map(normalizeReplayEvent);
      const computed = computeReplaySnapshots(normalized);

      setReplayEvents(normalized);
      setReplaySnapshots(computed);
      setReplayAnalysis(data.analysis || null);
      setReplayIndex(normalized.length > 0 ? 0 : -1);
      setReplayMode(true);
    } catch (err) {
      if (err.name === 'CanceledError' || err.name === 'AbortError') return;
      if (err.response && err.response.status === 409) {
        setReplayError("Replay unavailable: No events recorded.");
      } else if (err.response && err.response.status === 404) {
        setReplayError("Pipeline not found.");
      } else {
        setReplayError(err.message || "Failed to load replay.");
      }
    } finally {
      if (!controller.signal.aborted) {
        setReplayLoading(false);
      }
    }
  };

  const exitReplayMode = () => {
    setReplayPlaying(false);
    if (replayTimerRef.current) {
      clearTimeout(replayTimerRef.current);
      replayTimerRef.current = null;
    }
    setReplayMode(false);
    setReplayEvents([]);
    setReplaySnapshots([]);
    setReplayIndex(-1);
    setReplayAnalysis(null);
  };

  // Live Polling effect
  useEffect(() => {
    if (abortRef.current) abortRef.current.abort();
    clearInterval(intervalRef.current);

    if (!selectedPipelineId) {
      setTimelineEvents([]);
      setTimelineError(null);
      setTimelineLoading(false);
      return;
    }

    if (replayMode) {
      // Pause timeline polling during replay mode
      return;
    }

    setTimelineLoading(true);

    const poll = async () => {
      if (replayMode) return;
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
  }, [selectedPipelineId, refreshTrigger, replayMode]);

  return (
    <PipelineContext.Provider value={{
      selectedPipelineId,
      setSelectedPipelineId,
      pipelines,
      setPipelines,
      selectedTaskId,
      setSelectedTaskId,
      selectedTraceId,
      setSelectedTraceId,
      selectedWorkerId,
      setSelectedWorkerId,
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
      onRetryTask,
      
      // Replay exports
      replayMode,
      replayEvents,
      replayIndex,
      replaySnapshots,
      replayPlaying,
      replaySpeed,
      setReplaySpeed,
      replayAnalysis,
      replayError,
      replayLoading,
      startReplay,
      pauseReplay,
      seekReplay,
      stepForwardReplay,
      stepBackwardReplay,
      restartReplay,
      enterReplayMode,
      exitReplayMode
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
