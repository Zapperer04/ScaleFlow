import { useState, useEffect, useCallback } from 'react';
import { 
  fetchValidationStatus, pauseQueue, resumeQueue, 
  fetchPausedQueues, triggerLeaseExpiry, triggerManualRecovery, injectBurstLoad, 
  triggerBackpressure, triggerOrchestratorFailover, runSubprocessTest, 
  fetchSubprocessTestStatus 
} from '../../services/api';

// Chaos action definition registry
export const CHAOS_ACTIONS = {
  failover: {
    id: 'failover',
    title: 'Trigger Orchestrator Failover',
    description: 'Forces active HA coordinator to failover. Simulation will switch leadership to replacement replicas.',
    severity: 'danger', // maps to ConfirmDialog variant
    api: triggerOrchestratorFailover
  },
  leaseExpiry: {
    id: 'leaseExpiry',
    title: 'Inject Lease Expiry Chaos',
    description: 'Simulates connection drops on processing nodes, triggering automatic lock reclamation.',
    severity: 'danger',
    api: triggerLeaseExpiry
  },
  burstLoad: {
    id: 'burstLoad',
    title: 'Inject Burst Load Stress',
    description: 'Enqueues a sudden burst of tasks into Redis broker queues to test dynamic capacity scaling.',
    severity: 'warning',
    api: injectBurstLoad
  },
  backpressure: {
    id: 'backpressure',
    title: 'Force Queue Backpressure',
    description: 'Restricts task dispatch rates to simulate downstream worker capacity bottlenecks.',
    severity: 'warning',
    api: triggerBackpressure
  },
  manualRecovery: {
    id: 'manualRecovery',
    title: 'Trigger Manual Recovery Routine',
    description: 'Runs explicit reconciliation locks checks to reclaim stuck execution queues.',
    severity: 'primary',
    api: triggerManualRecovery
  }
};

export const useValidation = () => {
  const [validationItems, setValidationItems] = useState([]);
  const [pausedQueues, setPausedQueues] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Stress / HA Test Runner states
  const [selectedTest, setSelectedTest] = useState('validation');
  const [testStatus, setTestStatus] = useState('idle');
  const [testLogs, setTestLogs] = useState([]);
  const [isRunningTest, setIsRunningTest] = useState(false);

  // ConfirmDialog states
  const [confirmState, setConfirmState] = useState({ isOpen: false, title: '', message: '', variant: 'primary', onConfirm: null });

  // Operations Log
  const [operationsLog, setOperationsLog] = useState([
    { id: '1', timestamp: new Date(Date.now() - 3600000).toISOString(), title: 'System Validation Check', category: 'Validation', description: 'Automatic registry scan completed successfully.' }
  ]);

  const addLog = useCallback((category, title, description) => {
    setOperationsLog(prev => [
      {
        id: Math.random().toString(),
        timestamp: new Date().toISOString(),
        category,
        title,
        description
      },
      ...prev
    ]);
  }, []);

  const loadValidationStatus = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchValidationStatus();
      // Normalize validation checks list
      const items = [
        { id: 'redis', title: 'Redis Broker Connection', status: data.redis_connected ? 'healthy' : 'unhealthy', severity: 'danger', description: 'Verifies task queue messaging availability.' },
        { id: 'db', title: 'PostgreSQL Database Connection', status: data.postgres_connected ? 'healthy' : 'unhealthy', severity: 'danger', description: 'Verifies persistent transaction records storage.' },
        { id: 'qdrant', title: 'Qdrant Vector Database', status: data.qdrant_connected ? 'healthy' : 'unhealthy', severity: 'warning', description: 'Verifies similarity search indexing service.' },
        { id: 'workers', title: 'Active Worker Registries', status: data.has_active_workers ? 'healthy' : 'unhealthy', severity: 'danger', description: 'Verifies online cluster processing capacities.' }
      ];
      setValidationItems(items);
      setError(null);
    } catch (err) {
      console.error(err);
      setError('Failed to fetch validation status.');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadPausedQueues = useCallback(async () => {
    try {
      const data = await fetchPausedQueues();
      setPausedQueues(data || []);
    } catch (err) {
      console.error(err);
    }
  }, []);

  useEffect(() => {
    loadValidationStatus();
    loadPausedQueues();
  }, [loadValidationStatus, loadPausedQueues]);

  // Poll subprocess test status
  useEffect(() => {
    let intervalId;
    if (isRunningTest) {
      const pollTest = async () => {
        try {
          const data = await fetchSubprocessTestStatus(selectedTest);
          setTestStatus(data.status);
          setTestLogs(data.logs || []);
          if (data.status !== 'running') {
            setIsRunningTest(false);
            addLog('Tests', `Test completed: ${selectedTest}`, `Status result: ${data.status.toUpperCase()}`);
            loadValidationStatus();
          }
        } catch (err) {
          console.error(err);
        }
      };
      intervalId = setInterval(pollTest, 2000);
    }
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [isRunningTest, selectedTest, loadValidationStatus, addLog]);

  // Unified Chaos execution
  const executeChaosAction = useCallback((actionId) => {
    const config = CHAOS_ACTIONS[actionId];
    if (!config) return;

    setConfirmState({
      isOpen: true,
      title: config.title,
      message: `${config.description} Are you sure you want to execute this operations trigger?`,
      variant: config.severity,
      onConfirm: async () => {
        setConfirmState(prev => ({ ...prev, isOpen: false }));
        try {
          addLog('Chaos', `Executing Chaos: ${config.title}`, 'Operations payload dispatched to cluster controller.');
          await config.api();
          addLog('Chaos', `Executed Chaos Success: ${config.title}`, 'Trigger resolved successfully.');
          loadValidationStatus();
        } catch (err) {
          addLog('Chaos', `Executed Chaos Failed: ${config.title}`, err.message || 'API rejected trigger.');
        }
      }
    });
  }, [addLog, loadValidationStatus]);

  // Test Runner trigger
  const runTest = useCallback(async (testId) => {
    setIsRunningTest(true);
    setTestStatus('running');
    setTestLogs(['Spawning validation subprocess...']);
    addLog('Tests', `Started Subprocess Test Suite: ${testId}`, 'Runner worker thread initialized.');
    try {
      await runSubprocessTest(testId);
    } catch (err) {
      setIsRunningTest(false);
      setTestStatus('failed');
      addLog('Tests', `Failed Subprocess Test: ${testId}`, err.message || 'Failed to spawn thread.');
    }
  }, [addLog]);

  // Queue Pause / Resume
  const toggleQueueState = useCallback(async (queueName, isPaused) => {
    const actionLabel = isPaused ? 'Resume' : 'Pause';
    setConfirmState({
      isOpen: true,
      title: `${actionLabel} Queue: ${queueName}`,
      message: `Are you sure you want to ${actionLabel.toLowerCase()} execution dispatching on "${queueName}"?`,
      variant: 'info',
      onConfirm: async () => {
        setConfirmState(prev => ({ ...prev, isOpen: false }));
        try {
          if (isPaused) {
            await resumeQueue(queueName);
          } else {
            await pauseQueue(queueName);
          }
          addLog('Workers', `${actionLabel}d Queue: ${queueName}`, `Task queue state switched successfully.`);
          loadPausedQueues();
        } catch (err) {
          addLog('Workers', `Failed ${actionLabel} Queue: ${queueName}`, err.message || 'API error.');
        }
      }
    });
  }, [addLog, loadPausedQueues]);

  return {
    data: {
      validationItems,
      pausedQueues,
      selectedTest,
      testStatus,
      testLogs,
      isRunningTest,
      confirmState,
      operationsLog
    },
    loading,
    error,
    actions: {
      setSelectedTest,
      setConfirmState,
      executeChaosAction,
      runTest,
      toggleQueueState,
      addLog
    }
  };
};
export default useValidation;
