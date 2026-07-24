import { apiClient } from './apiClient';

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

export const globalSearch = async (query) => {
  const response = await apiClient.post('/api/v1/search/global', { query });
  return response.data;
};

export const createQueryPipelineV1 = async (queryData) => {
  const response = await apiClient.post('/api/v1/query-pipelines', queryData);
  return response.data;
};

export const fetchQueryPipelineAnswerV1 = async (pipelineId) => {
  const response = await apiClient.get(`/api/v1/query-pipelines/${pipelineId}/answer`);
  return response.data;
};

export const explainQueryPipeline = async (pipelineId) => {
  const response = await apiClient.get(`/api/v1/query-pipelines/${pipelineId}/explain`);
  return response.data;
};
