import { apiClient } from './apiClient';

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

export const fetchPdfContent = async (fileId) => {
  const response = await apiClient.get(`/api/v1/files/${fileId}/content`, {
    responseType: 'blob'
  });
  return response.data;
};
