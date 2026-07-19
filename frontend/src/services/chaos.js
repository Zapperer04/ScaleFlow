import { apiClient } from './apiClient';

export const getQueueStats = async () => {
  const response = await apiClient.get('/queues/stats');
  return response.data;
};

export const getDatabaseStatus = async () => {
  const response = await apiClient.get('/database/status');
  return response.data;
};

export const getClusterStatus = async () => {
  const response = await apiClient.get('/cluster/status');
  return response.data;
};

export const getClusterFailovers = async () => {
  const response = await apiClient.get('/cluster/failovers');
  return response.data;
};

export const fetchValidationStatus = async () => {
  const response = await apiClient.get('/validation/check');
  return response.data;
};

export const killWorker = async (workerId) => {
  const response = await apiClient.post('/chaos/kill-worker', { worker_id: workerId });
  return response.data;
};

export const startWorker = async (workerId) => {
  const response = await apiClient.post('/chaos/start-worker', { worker_id: workerId });
  return response.data;
};

export const pauseQueue = async (queueName) => {
  const response = await apiClient.post('/chaos/pause-queue', { queue_name: queueName });
  return response.data;
};

export const resumeQueue = async (queueName) => {
  const response = await apiClient.post('/chaos/resume-queue', { queue_name: queueName });
  return response.data;
};

export const fetchPausedQueues = async () => {
  const response = await apiClient.get('/chaos/paused-queues');
  return response.data;
};

export const triggerLeaseExpiry = async () => {
  const response = await apiClient.post('/chaos/expire-lease');
  return response.data;
};

export const triggerManualRecovery = async () => {
  const response = await apiClient.post('/chaos/trigger-recovery');
  return response.data;
};

export const injectBurstLoad = async (count = 30) => {
  const response = await apiClient.post('/chaos/inject-burst', { count });
  return response.data;
};

export const triggerBackpressure = async (enable = true) => {
  const response = await apiClient.post('/chaos/trigger-backpressure', { enable });
  return response.data;
};

export const triggerOrchestratorFailover = async () => {
  const response = await apiClient.post('/chaos/failover');
  return response.data;
};

// Subprocess Test Runner endpoints
export const runSubprocessTest = async (testType) => {
  const response = await apiClient.post(`/tests/run/${testType}`);
  return response.data;
};

export const fetchSubprocessTestStatus = async (testType) => {
  const response = await apiClient.get(`/tests/status/${testType}`);
  return response.data;
};
