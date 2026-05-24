import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
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
