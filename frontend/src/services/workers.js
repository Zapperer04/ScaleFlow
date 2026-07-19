import { apiClient } from './apiClient';

export const fetchWorkers = async () => {
  const response = await apiClient.get('/workers');
  return response.data;
};

export const getWorkersRegistry = async () => {
  const response = await apiClient.get('/workers/registry');
  return response.data;
};
