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
