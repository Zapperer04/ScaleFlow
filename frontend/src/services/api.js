import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:5000';
const API_KEY = process.env.REACT_APP_API_KEY || 'dev_secret_api_key';

const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'X-API-Key': API_KEY,
    'Content-Type': 'application/json'
  }
});

export const fetchTasks = async (page = 1, limit = 50) => {
  const response = await apiClient.get(`/tasks?page=${page}&limit=${limit}`);
  return response.data;
};

export const fetchWorkers = async () => {
  const response = await apiClient.get('/workers');
  return response.data;
};

export const fetchTaskTypes = async () => {
  const response = await apiClient.get('/task-types');
  return response.data;
};

export const createTask = async (taskData) => {
  const response = await apiClient.post('/tasks', taskData);
  return response.data;
};

export const getQueueStats = async () => {
  const response = await apiClient.get('/queues/stats');
  return response.data;
};

export const getTaskDetails = async (taskId) => {
  const response = await apiClient.get(`/tasks/${taskId}/details`);
  return response.data;
};

export const retryTask = async (taskId, force = false) => {
  const response = await apiClient.post(`/tasks/${taskId}/retry`, { force });
  return response.data;
};

export const cancelTask = async (taskId) => {
  const response = await apiClient.post(`/tasks/${taskId}/cancel`);
  return response.data;
};

export const runIntegrationTests = async () => {
  const response = await apiClient.get('/tasks/test-recovery');
  return response.data;
};

export const fetchPipelines = async () => {
  const response = await apiClient.get('/pipelines');
  return response.data;
};

export const fetchPipelineDetails = async (pipelineId) => {
  const response = await apiClient.get(`/pipelines/${pipelineId}`);
  return response.data;
};

export const fetchPipelineDag = async (pipelineId) => {
  const response = await apiClient.get(`/pipelines/${pipelineId}/dag`);
  return response.data;
};

export const createPipeline = async (pipelineData) => {
  const response = await apiClient.post('/pipelines', pipelineData);
  return response.data;
};

export const cancelPipeline = async (pipelineId) => {
  const response = await apiClient.post(`/pipelines/${pipelineId}/cancel`);
  return response.data;
};

export const runPipelineTests = async () => {
  const response = await apiClient.post('/pipelines/test-dag');
  return response.data;
};

export const fetchArtifactContent = async (artifactId) => {
  const response = await apiClient.get(`/artifacts/${artifactId}/content`);
  return response.data;
};

export const uploadFile = async (formData) => {
  const response = await apiClient.post('/files/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  });
  return response.data;
};

export const fetchUploadedFiles = async () => {
  const response = await apiClient.get('/files');
  return response.data;
};

export const fetchUploadedFileDetail = async (fileId) => {
  const response = await apiClient.get(`/files/${fileId}`);
  return response.data;
};

export const searchVectors = async (query, topK = 5, pipelineId = null, fileId = null) => {
  const payload = { query, top_k: topK };
  if (pipelineId !== null && pipelineId !== undefined) {
    payload.pipeline_id = pipelineId;
  }
  if (fileId !== null && fileId !== undefined) {
    payload.file_id = fileId;
  }
  const response = await apiClient.post('/search', payload);
  return response.data;
};

export const fetchVectorStats = async () => {
  const response = await apiClient.get('/vectors/stats');
  return response.data;
};

export const createRetrievalPipeline = async (queryData) => {
  const response = await apiClient.post('/query-pipelines', queryData);
  return response.data;
};

export const fetchRetrievalPipelineAnswer = async (pipelineId) => {
  const response = await apiClient.get(`/query-pipelines/${pipelineId}/answer`);
  return response.data;
};

export const fetchPipelineTimeline = async (pipelineId) => {
  const response = await apiClient.get(`/pipelines/${pipelineId}/timeline`);
  return response.data;
};

export const retryPipeline = async (pipelineId) => {
  const response = await apiClient.post(`/pipelines/${pipelineId}/retry`);
  return response.data;
};

export const getSystemMetrics = async () => {
  const response = await apiClient.get('/metrics/system');
  return response.data;
};

export const getQueueMetrics = async () => {
  const response = await apiClient.get('/metrics/queues');
  return response.data;
};

export const getWorkerMetrics = async () => {
  const response = await apiClient.get('/metrics/workers');
  return response.data;
};

export const getScalingMetrics = async () => {
  const response = await apiClient.get('/metrics/scaling');
  return response.data;
};

export const getPipelineMetrics = async (pipelineId) => {
  const response = await apiClient.get(`/metrics/pipelines/${pipelineId}`);
  return response.data;
};

export const getBackpressureMetrics = async () => {
  const response = await apiClient.get('/metrics/backpressure');
  return response.data;
};

export const fetchEvents = async (category = '', pipelineId = '') => {
  const response = await apiClient.get(`/events?category=${category}&pipeline_id=${pipelineId}`);
  return response.data;
};

export const fetchPipelineEvents = async (pipelineId) => {
  const response = await apiClient.get(`/events/pipelines/${pipelineId}`);
  return response.data;
};

export const fetchWorkerEvents = async (workerId) => {
  const response = await apiClient.get(`/events/workers/${workerId}`);
  return response.data;
};

export const fetchSnapshots = async (pipelineId = '') => {
  const response = await apiClient.get(`/snapshots?pipeline_id=${pipelineId}`);
  return response.data;
};

export const fetchPipelineSnapshots = async (pipelineId) => {
  const response = await apiClient.get(`/snapshots/pipelines/${pipelineId}`);
  return response.data;
};

export const triggerPipelineSnapshot = async (pipelineId) => {
  const response = await apiClient.post(`/snapshots/pipelines/${pipelineId}/create`);
  return response.data;
};

export const fetchReplayDetails = async (pipelineId) => {
  const response = await apiClient.get(`/replay/pipelines/${pipelineId}`);
  return response.data;
};

export const startReplay = async (pipelineId) => {
  const response = await apiClient.post(`/replay/pipelines/${pipelineId}/start`);
  return response.data;
};

export const pauseReplay = async (pipelineId) => {
  const response = await apiClient.post(`/replay/pipelines/${pipelineId}/pause`);
  return response.data;
};

export const stepReplay = async (pipelineId) => {
  const response = await apiClient.post(`/replay/pipelines/${pipelineId}/step`);
  return response.data;
};

export const fetchReconstructedState = async (pipelineId, targetEventId = null, targetTime = null) => {
  let url = `/replay/pipelines/${pipelineId}/state`;
  const params = [];
  if (targetEventId !== null && targetEventId !== undefined) {
    params.push(`target_event_id=${targetEventId}`);
  }
  if (targetTime !== null && targetTime !== undefined) {
    params.push(`target_time=${encodeURIComponent(targetTime)}`);
  }
  if (params.length > 0) {
    url += `?${params.join('&')}`;
  }
  const response = await apiClient.get(url);
  return response.data;
};

export const getClusterStatus = async () => {
  const response = await apiClient.get('/cluster/status');
  return response.data;
};

export const getWorkersRegistry = async () => {
  const response = await apiClient.get('/workers/registry');
  return response.data;
};

export const getClusterFailovers = async () => {
  const response = await apiClient.get('/cluster/failovers');
  return response.data;
};

export const getDatabaseStatus = async () => {
  const response = await apiClient.get('/database/status');
  return response.data;
};

// System Validation & Chaos endpoints
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
