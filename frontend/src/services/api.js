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
