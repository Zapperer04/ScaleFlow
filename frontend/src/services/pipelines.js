import { apiClient } from './apiClient';

export const fetchTasks = async (page = 1, limit = 50) => {
  const response = await apiClient.get(`/tasks?page=${page}&limit=${limit}`);
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

export const normalizeArtifact = (rawArt) => {
  if (!rawArt) return null;

  let metadata = rawArt.metadata_json || {};
  if (typeof metadata === 'string') {
    try {
      metadata = JSON.parse(metadata);
    } catch (e) {
      metadata = {};
    }
  }

  const rawVal = metadata.validation || {};
  const validation = {
    is_valid: rawVal.is_valid !== false,
    error_code: rawVal.error_code || null,
    error_message: rawVal.error_message || null,
    validated_at: rawVal.validated_at || rawArt.created_at || new Date().toISOString(),
    validator_version: rawVal.validator_version || "1"
  };

  return {
    ...rawArt,
    metadata_json: {
      ...metadata,
      validation
    }
  };
};

export const fetchPipelineDetails = async (pipelineId, signal) => {
  const response = await apiClient.get(`/pipelines/${pipelineId}`, { signal });
  const data = response.data;
  if (data && Array.isArray(data.artifacts)) {
    data.artifacts = data.artifacts.map(normalizeArtifact);
  }
  return data;
};

export const fetchPipelineDag = async (pipelineId, signal) => {
  const response = await apiClient.get(`/pipelines/${pipelineId}/dag`, { signal });
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

export const fetchPipelineTimeline = async (pipelineId, signal) => {
  const response = await apiClient.get(`/pipelines/${pipelineId}/timeline`, { signal });
  if (response.data && Array.isArray(response.data.timeline)) {
    const arr = response.data.timeline;
    arr.correlation = response.data.correlation;
    return arr;
  }
  return response.data;
};

export const retryPipeline = async (pipelineId) => {
  const response = await apiClient.post(`/pipelines/${pipelineId}/retry`);
  return response.data;
};

export const fetchPipelineReplay = async (pipelineId, signal) => {
  const response = await apiClient.get(`/pipelines/${pipelineId}/replay`, { signal });
  return response.data;
};

export const fetchPipelinePerformance = async (pipelineId, signal) => {
  const response = await apiClient.get(`/pipelines/${pipelineId}/performance`, { signal });
  return response.data;
};

export const fetchPipelineOptimization = async (pipelineId, signal) => {
  const response = await apiClient.get(`/pipelines/${pipelineId}/optimization`, { signal });
  return response.data;
};

export const fetchPipelineForecast = async (pipelineId, signal) => {
  const response = await apiClient.get(`/pipelines/${pipelineId}/forecast`, { signal });
  return response.data;
};

export const fetchPipelineAdvisor = async (pipelineId, signal) => {
  const response = await apiClient.get(`/pipelines/${pipelineId}/advisor`, { signal });
  return response.data;
};




