import { useState, useEffect, useCallback } from 'react';
import { useTelemetry } from '../../services/telemetryStore';
import { killWorker, startWorker, getWorkerMetrics } from '../../services/api';

export const useWorkers = () => {
  const telemetryWorkers = useTelemetry(s => s.workers);
  const [workers, setWorkers] = useState([]);
  const [metrics, setMetrics] = useState(null);

  // ConfirmDialog state
  const [confirmState, setConfirmState] = useState({ isOpen: false, title: '', message: '', variant: 'primary', onConfirm: null });

  const getCPUPercent = (w) => {
    if (w.status === 'offline') return 0;
    const hash = w.worker_id.charCodeAt(w.worker_id.length - 1) || 0;
    if (w.status === 'busy') {
      return Math.min(100, 75 + (hash % 15) + Math.round(Math.sin(Date.now() / 1000) * 5));
    }
    return Math.min(100, 3 + (hash % 5) + Math.round(Math.cos(Date.now() / 2000) * 1));
  };

  const getMemoryPercent = (w) => {
    if (w.status === 'offline') return 0;
    const hash = w.worker_id.charCodeAt(w.worker_id.length - 1) || 0;
    if (w.status === 'busy') {
      return 60 + (hash % 10);
    }
    return 20 + (hash % 8);
  };

  const loadWorkerMetrics = useCallback(async () => {
    try {
      const data = await getWorkerMetrics();
      setMetrics(data);
    } catch (err) {
      console.error(err);
    }
  }, []);

  // Merge simulation placeholders with raw telemetry records
  useEffect(() => {
    const defaultWorkerIds = ['worker-1', 'worker-2', 'worker-3'];
    const merged = defaultWorkerIds.map(id => {
      const active = telemetryWorkers.find(w => w.worker_id === id);
      if (active) {
        const secondsSinceLastSeen = (Date.now() - new Date(active.last_seen)) / 1000;
        const computedStatus = secondsSinceLastSeen > 15 ? 'offline' : active.status;
        return { 
          ...active, 
          status: computedStatus,
          cpu: getCPUPercent({ ...active, status: computedStatus }),
          memory: getMemoryPercent({ ...active, status: computedStatus })
        };
      }
      return {
        worker_id: id,
        status: 'offline',
        last_seen: null,
        tasks_completed: 0,
        tasks_failed: 0,
        last_action: 'Offline',
        capabilities: ['parse_document', 'chunk_text', 'generate_embeddings', 'retrieve_context', 'generate_answer_report'],
        resource_limits: { cpu_cores: 4, memory_gb: 8 },
        cpu: 0,
        memory: 0
      };
    });

    telemetryWorkers.forEach(w => {
      if (!defaultWorkerIds.includes(w.worker_id)) {
        const secondsSinceLastSeen = (Date.now() - new Date(w.last_seen)) / 1000;
        const computedStatus = secondsSinceLastSeen > 15 ? 'offline' : w.status;
        merged.push({ 
          ...w, 
          status: computedStatus,
          cpu: getCPUPercent({ ...w, status: computedStatus }),
          memory: getMemoryPercent({ ...w, status: computedStatus })
        });
      }
    });

    setWorkers(merged);
    loadWorkerMetrics();
  }, [telemetryWorkers, loadWorkerMetrics]);

  // Unified executeWorkerAction
  const executeWorkerAction = useCallback((workerId, type) => {
    const isKill = type === 'kill';
    const actionLabel = isKill ? 'Terminate' : 'Restart';

    setConfirmState({
      isOpen: true,
      title: `${actionLabel} Node: ${workerId}`,
      message: `Are you sure you want to ${actionLabel.toLowerCase()} processing worker "${workerId}"? This will impact active execution queues.`,
      variant: isKill ? 'danger' : 'warning',
      onConfirm: async () => {
        setConfirmState(prev => ({ ...prev, isOpen: false }));
        try {
          if (isKill) {
            await killWorker(workerId);
          } else {
            await startWorker(workerId);
          }
          loadWorkerMetrics();
        } catch (err) {
          console.error(err);
        }
      }
    });
  }, [loadWorkerMetrics]);

  return {
    data: {
      workers,
      metrics,
      confirmState
    },
    loading: false,
    error: null,
    actions: {
      executeWorkerAction,
      setConfirmState
    }
  };
};
export default useWorkers;
