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

export const fetchPipelineTimeline = async (pipelineId) => {
  const response = await apiClient.get(`/pipelines/${pipelineId}/timeline`);
  return response.data;
};

export const retryPipeline = async (pipelineId) => {
  const response = await apiClient.post(`/pipelines/${pipelineId}/retry`);
  return response.data;
};
