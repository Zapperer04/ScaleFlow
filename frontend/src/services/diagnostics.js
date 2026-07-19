import { apiClient } from './apiClient';

export const fetchArtifactContent = async (artifactId) => {
  const response = await apiClient.get(`/artifacts/${artifactId}/content`);
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
