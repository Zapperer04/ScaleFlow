import React, { createContext, useState, useContext, useEffect, useRef, useMemo } from 'react';
import { fetchPipelineTimeline, retryTask, fetchPipelineReplay, fetchPipelinePerformance, fetchPipelineOptimization } from '../services/pipelines';

const PipelineContext = createContext(null);

export const computeSnapshotDiff = (snapA, snapB) => {
  if (!snapA || !snapB) {
    return {
      tasks: [],
      workers: [],
      retryDelta: 0,
      queueChanges: [],
      progressChanges: []
    };
  }

  const tasksDiff = [];
  const workersDiff = [];
  let retryDelta = 0;
  const queueChanges = [];
  const progressChanges = [];

  // Get union of all task IDs
  const allTaskIds = Array.from(new Set([
    ...Object.keys(snapA.taskStates || {}),
    ...Object.keys(snapB.taskStates || {})
  ]));

  for (const taskId of allTaskIds) {
    const taskA = snapA.taskStates?.[taskId] || {
      status: 'pending',
      workerId: null,
      retryCount: 0,
      queue: null,
      progress: null
    };
    const taskB = snapB.taskStates?.[taskId] || {
      status: 'pending',
      workerId: null,
      retryCount: 0,
      queue: null,
      progress: null
    };

    // 1. Task Status
    if (taskA.status !== taskB.status) {
      tasksDiff.push({
        taskId,
        field: 'status',
        before: taskA.status,
        after: taskB.status
      });
    }

    // 2. Worker Assignment
    if (taskA.workerId !== taskB.workerId) {
      tasksDiff.push({
        taskId,
        field: 'workerId',
        before: taskA.workerId,
        after: taskB.workerId
      });
    }

    // 3. Retry Count (mutually exclusive retryDelta)
    if (taskA.retryCount !== taskB.retryCount) {
      retryDelta += (taskB.retryCount - taskA.retryCount);
    }

    // 4. Queue
    if (taskA.queue !== taskB.queue) {
      queueChanges.push({
        taskId,
        before: taskA.queue,
        after: taskB.queue
      });
    }

    // 5. Progress
    if (taskA.progress !== taskB.progress) {
      progressChanges.push({
        taskId,
        before: taskA.progress,
        after: taskB.progress
      });
    }
  }

  // Get union of all worker IDs
  const allWorkerIds = Array.from(new Set([
    ...Object.keys(snapA.workerStates || {}),
    ...Object.keys(snapB.workerStates || {})
  ]));

  for (const wId of allWorkerIds) {
    const workerA = snapA.workerStates?.[wId] || {
      state: 'idle',
      currentTask: null,
      leaseStatus: 'valid'
    };
    const workerB = snapB.workerStates?.[wId] || {
      state: 'idle',
      currentTask: null,
      leaseStatus: 'valid'
    };

    if (
      workerA.state !== workerB.state ||
      workerA.currentTask !== workerB.currentTask ||
      workerA.leaseStatus !== workerB.leaseStatus
    ) {
      workersDiff.push({
        workerId: wId,
        before: {
          state: workerA.state,
          currentTask: workerA.currentTask,
          leaseStatus: workerA.leaseStatus
        },
        after: {
          state: workerB.state,
          currentTask: workerB.currentTask,
          leaseStatus: workerB.leaseStatus
        }
      });
    }
  }

  return {
    tasks: tasksDiff,
    workers: workersDiff,
    retryDelta,
    queueChanges,
    progressChanges
  };
};


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
    snapshots.push(Object.freeze(snapshot));
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

  // Performance Analytics Hooks
  const [performanceModel, setPerformanceModel] = useState(null);
  const [performanceLoading, setPerformanceLoading] = useState(false);
  const [performanceError, setPerformanceError] = useState(null);
  const [timelineZoom, setTimelineZoom] = useState(0.1); // pixels per ms
  const [timelineOffset, setTimelineOffset] = useState(0);
  const [selectedPerformanceSpanId, setSelectedPerformanceSpanId] = useState(null);
  const abortPerformanceFetchRef = useRef(null);

  // Optimization Hooks
  const [optimizationModel, setOptimizationModel] = useState(null);
  const [optimizationLoading, setOptimizationLoading] = useState(false);
  const [optimizationError, setOptimizationError] = useState(null);
  const abortOptimizationFetchRef = useRef(null);

  // Time-Travel Comparison State Hooks
  const [selectedSnapshotAIndex, setSelectedSnapshotAIndex] = useState(null);
  const [selectedSnapshotBIndex, setSelectedSnapshotBIndex] = useState(null);

  const comparisonMode = selectedSnapshotAIndex !== null && selectedSnapshotBIndex !== null;

  const diffCacheRef = useRef({});

  const snapshotDiff = useMemo(() => {
    if (!comparisonMode || !replaySnapshots || selectedSnapshotAIndex === null || selectedSnapshotBIndex === null) {
      return {
        tasks: [],
        workers: [],
        retryDelta: 0,
        queueChanges: [],
        progressChanges: []
      };
    }
    // Bounds check
    if (selectedSnapshotAIndex < 0 || selectedSnapshotAIndex >= replaySnapshots.length ||
        selectedSnapshotBIndex < 0 || selectedSnapshotBIndex >= replaySnapshots.length) {
      return {
        tasks: [],
        workers: [],
        retryDelta: 0,
        queueChanges: [],
        progressChanges: []
      };
    }

    const key = `${selectedSnapshotAIndex}|${selectedSnapshotBIndex}`;
    if (diffCacheRef.current[key]) {
      return diffCacheRef.current[key];
    }

    const snapA = replaySnapshots[selectedSnapshotAIndex];
    const snapB = replaySnapshots[selectedSnapshotBIndex];
    const diff = computeSnapshotDiff(snapA, snapB);
    diffCacheRef.current[key] = diff;
    return diff;
  }, [replaySnapshots, selectedSnapshotAIndex, selectedSnapshotBIndex, comparisonMode]);

  // Freeze automatic replay-driven selections in comparison mode
  useEffect(() => {
    if (replayMode && !comparisonMode && replaySnapshots && replayIndex >= 0 && replayIndex < replaySnapshots.length) {
      const snap = replaySnapshots[replayIndex];
      if (snap.selectedTaskId !== undefined) setSelectedTaskId(snap.selectedTaskId);
      if (snap.selectedWorkerId !== undefined) setSelectedWorkerId(snap.selectedWorkerId);
      if (snap.selectedTraceId !== undefined) setSelectedTraceId(snap.selectedTraceId);
    }
  }, [replayIndex, replayMode, comparisonMode, replaySnapshots]);


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
    setSelectedSnapshotAIndex(null);
    setSelectedSnapshotBIndex(null);
    diffCacheRef.current = {};
    if (abortPerformanceFetchRef.current) {
      abortPerformanceFetchRef.current.abort();
    }
    if (abortOptimizationFetchRef.current) {
      abortOptimizationFetchRef.current.abort();
    }
    setPerformanceModel(null);
    setPerformanceLoading(false);
    setPerformanceError(null);
    setSelectedPerformanceSpanId(null);
    setOptimizationModel(null);
    setOptimizationLoading(false);
    setOptimizationError(null);
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
      
      // Invalidate performance & optimization cache when replay is loaded/regenerated
      if (abortPerformanceFetchRef.current) {
        abortPerformanceFetchRef.current.abort();
      }
      if (abortOptimizationFetchRef.current) {
        abortOptimizationFetchRef.current.abort();
      }
      setPerformanceModel(null);
      setPerformanceError(null);
      setSelectedPerformanceSpanId(null);
      setOptimizationModel(null);
      setOptimizationError(null);
      
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
    setSelectedSnapshotAIndex(null);
    setSelectedSnapshotBIndex(null);
    diffCacheRef.current = {};
    if (abortPerformanceFetchRef.current) {
      abortPerformanceFetchRef.current.abort();
    }
    if (abortOptimizationFetchRef.current) {
      abortOptimizationFetchRef.current.abort();
    }
    setPerformanceModel(null);
    setPerformanceLoading(false);
    setPerformanceError(null);
    setSelectedPerformanceSpanId(null);
    setOptimizationModel(null);
    setOptimizationLoading(false);
    setOptimizationError(null);
  };

  const loadPerformance = async () => {
    if (!selectedPipelineId) return;
    if (performanceModel && performanceModel.pipeline_id === selectedPipelineId) {
      return; // cached
    }
    if (abortPerformanceFetchRef.current) {
      abortPerformanceFetchRef.current.abort();
    }
    const controller = new AbortController();
    abortPerformanceFetchRef.current = controller;
    
    setPerformanceLoading(true);
    setPerformanceError(null);
    try {
      const data = await fetchPipelinePerformance(selectedPipelineId, controller.signal);
      if (controller.signal.aborted) return;
      setPerformanceModel(data);
    } catch (err) {
      if (err.name === 'CanceledError' || err.name === 'AbortError') return;
      if (err.response && err.response.status === 409) {
        setPerformanceError("Performance analytics unavailable: Replay unavailable.");
      } else if (err.response && err.response.status === 404) {
        setPerformanceError("Pipeline not found.");
      } else {
        setPerformanceError(err.message || "Failed to load performance analytics.");
      }
    } finally {
      if (!controller.signal.aborted) {
        setPerformanceLoading(false);
      }
    }
  };

  const loadOptimization = async () => {
    if (!selectedPipelineId) return;
    if (optimizationModel && optimizationModel.pipeline_id === selectedPipelineId) {
      return; // cached
    }
    if (abortOptimizationFetchRef.current) {
      abortOptimizationFetchRef.current.abort();
    }
    const controller = new AbortController();
    abortOptimizationFetchRef.current = controller;
    
    setOptimizationLoading(true);
    setOptimizationError(null);
    try {
      const data = await fetchPipelineOptimization(selectedPipelineId, controller.signal);
      if (controller.signal.aborted) return;
      setOptimizationModel(data);
    } catch (err) {
      if (err.name === 'CanceledError' || err.name === 'AbortError') return;
      if (err.response && err.response.status === 409) {
        setOptimizationError("Optimization analysis unavailable: Replay unavailable.");
      } else if (err.response && err.response.status === 404) {
        setOptimizationError("Pipeline not found.");
      } else {
        setOptimizationError(err.message || "Failed to load optimization analysis.");
      }
    } finally {
      if (!controller.signal.aborted) {
        setOptimizationLoading(false);
      }
    }
  };

  // Synchronize selection state when span changes
  useEffect(() => {
    if (!selectedPerformanceSpanId || !performanceModel) return;
    const timeline = performanceModel?.performance?.timeline || [];
    const seg = timeline.find(s => s.segment_id === selectedPerformanceSpanId);
    if (seg) {
      setSelectedTaskId(seg.task_id);
      if (replayEvents && replayEvents.length > 0) {
        const eventIndex = replayEvents.findIndex(e => String(e.task_id) === String(seg.task_id) && e.timestamp === seg.started_at);
        if (eventIndex !== -1) {
          seekReplay(eventIndex);
        } else {
          const fallbackIdx = replayEvents.findIndex(e => String(e.task_id) === String(seg.task_id));
          if (fallbackIdx !== -1) {
            seekReplay(fallbackIdx);
          }
        }
      }
    }
  }, [selectedPerformanceSpanId, performanceModel, replayEvents]);


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

  const selectSnapshotAIndex = (idx) => {
    setReplayPlaying(false);
    if (replaySnapshots && idx >= 0 && idx < replaySnapshots.length) {
      setSelectedSnapshotAIndex(idx);
    } else {
      setSelectedSnapshotAIndex(null);
    }
  };

  const selectSnapshotBIndex = (idx) => {
    setReplayPlaying(false);
    if (replaySnapshots && idx >= 0 && idx < replaySnapshots.length) {
      setSelectedSnapshotBIndex(idx);
    } else {
      setSelectedSnapshotBIndex(null);
    }
  };

  const swapSnapshots = () => {
    const temp = selectedSnapshotAIndex;
    setSelectedSnapshotAIndex(selectedSnapshotBIndex);
    setSelectedSnapshotBIndex(temp);
  };

  const clearComparison = () => {
    setSelectedSnapshotAIndex(null);
    setSelectedSnapshotBIndex(null);
  };

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
      exitReplayMode,

      // Comparison exports
      selectedSnapshotAIndex,
      setSelectedSnapshotAIndex,
      selectedSnapshotBIndex,
      setSelectedSnapshotBIndex,
      comparisonMode,
      snapshotDiff,
      selectSnapshotAIndex,
      selectSnapshotBIndex,
      swapSnapshots,
      clearComparison,

      // Performance exports
      performanceModel,
      performanceLoading,
      performanceError,
      timelineZoom,
      setTimelineZoom,
      timelineOffset,
      setTimelineOffset,
      selectedPerformanceSpanId,
      setSelectedPerformanceSpanId,
      loadPerformance,

      // Optimization exports
      optimizationModel,
      optimizationLoading,
      optimizationError,
      loadOptimization
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
