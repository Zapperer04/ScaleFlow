import { fetchTasks, fetchWorkers, getQueueStats, fetchPipelines, getDatabaseStatus, fetchVectorStats, getClusterStatus } from './api';
import { telemetryStore } from './telemetryStore';

let fastIntervalId = null;
let slowIntervalId = null;
let callbacksRef = { setPipelines: null, setShowStuckWarning: null };

const loadFastData = async () => {
  // 1. Fetch Tasks
  try {
    const tasksData = await fetchTasks(1, 50);
    const tasksList = tasksData.tasks || [];
    const metadata = tasksData.metadata || { total_tasks: 0 };
    telemetryStore.setState({
      stats: {
        total: metadata.total_tasks,
        pending: tasksList.filter(t => t.status === 'pending').length,
        running: tasksList.filter(t => t.status === 'running').length,
        completed: tasksList.filter(t => t.status === 'completed').length
      }
    });
  } catch (error) {
    console.warn('loadFastData: fetchTasks failed', error);
  }

  // 2. Fetch Pipelines
  try {
    const pipelinesData = await fetchPipelines();
    if (callbacksRef.setPipelines) {
      callbacksRef.setPipelines(pipelinesData);
    }
  } catch (error) {
    console.warn('loadFastData: fetchPipelines failed', error);
  }

  // 3. Fetch Workers
  let mergedWorkers = [];
  try {
    const workersData = await fetchWorkers();
    const defaultWorkerIds = ['worker-1', 'worker-2', 'worker-3'];
    mergedWorkers = defaultWorkerIds.map(id => {
      const active = workersData.find(w => w.worker_id === id);
      if (active) {
        const secondsSinceLastSeen = (Date.now() - new Date(active.last_seen)) / 1000;
        const computedStatus = secondsSinceLastSeen > 15 ? 'offline' : active.status;
        return { ...active, status: computedStatus };
      }
      return {
        worker_id: id,
        status: 'offline',
        last_seen: null,
        tasks_completed: 0,
        tasks_failed: 0,
        last_action: 'Offline'
      };
    });
    workersData.forEach(w => {
      if (!defaultWorkerIds.includes(w.worker_id)) {
        const secondsSinceLastSeen = (Date.now() - new Date(w.last_seen)) / 1000;
        const computedStatus = secondsSinceLastSeen > 15 ? 'offline' : w.status;
        mergedWorkers.push({ ...w, status: computedStatus });
      }
    });
    telemetryStore.setState({ workers: mergedWorkers });
  } catch (error) {
    console.warn('loadFastData: fetchWorkers failed', error);
  }

  // 4. Fetch Queue Stats & determine Redis status
  try {
    const qs = await getQueueStats();
    const redisOnline = qs.redis_status ? qs.redis_status === 'online' : true;
    telemetryStore.setState({
      queueStats: qs,
      redisStatus: redisOnline ? 'online' : 'offline'
    });

    const totalQueued = qs.total || 0;
    const allWorkersIdle = mergedWorkers.length > 0 && mergedWorkers.every(w => w.status === 'idle' || w.status === 'offline');
    if (totalQueued > 0 && allWorkersIdle) {
      if (callbacksRef.setShowStuckWarning) {
        callbacksRef.setShowStuckWarning(true);
      }
    } else {
      if (callbacksRef.setShowStuckWarning) {
        callbacksRef.setShowStuckWarning(false);
      }
    }
  } catch (error) {
    console.error('loadFastData: getQueueStats failed — Redis may be offline', error);
    telemetryStore.setState({ redisStatus: 'offline' });
  }
};

const loadSlowData = async () => {
  // 1. Check Database connection
  try {
    const db = await getDatabaseStatus();
    telemetryStore.setState({ dbStatus: db.status === 'connected' ? 'online' : 'offline' });
  } catch {
    telemetryStore.setState({ dbStatus: 'offline' });
  }

  // 2. Check Qdrant connection
  try {
    const qdrant = await fetchVectorStats();
    telemetryStore.setState({ qdrantStatus: qdrant.status === 'ok' ? 'online' : 'offline' });
  } catch {
    telemetryStore.setState({ qdrantStatus: 'offline' });
  }

  // 3. Check Cluster status
  try {
    const cluster = await getClusterStatus();
    telemetryStore.setState({
      leaderId: cluster.leader_instance_id || 'None',
      orchestratorCount: cluster.orchestrators?.length || 0
    });
  } catch {
    telemetryStore.setState({
      leaderId: 'Unknown',
      orchestratorCount: 0
    });
  }
};

export const pollingManager = {
  start: (callbacks, pollIntervalMs = 3000) => {
    callbacksRef = { ...callbacksRef, ...callbacks };
    
    // Trigger initial updates
    loadFastData();
    loadSlowData();

    // Start polling intervals
    if (!fastIntervalId) {
      fastIntervalId = setInterval(loadFastData, pollIntervalMs);
    }
    if (!slowIntervalId) {
      slowIntervalId = setInterval(loadSlowData, 10000);
    }
  },
  stop: () => {
    if (fastIntervalId) {
      clearInterval(fastIntervalId);
      fastIntervalId = null;
    }
    if (slowIntervalId) {
      clearInterval(slowIntervalId);
      slowIntervalId = null;
    }
  },
  triggerFastUpdate: () => {
    loadFastData();
  }
};
