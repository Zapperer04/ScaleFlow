import { apiClient } from './apiClient';

/**
 * Upload a file.
 *
 * KEY RULES:
 * 1. Do NOT set Content-Type manually — axios auto-generates
 *    "multipart/form-data; boundary=----abc123".
 *    Manually setting it strips the boundary and Flask cannot parse the body.
 *
 * 2. The upload endpoint returns { file_id, pipeline_id, ... }.
 *    We then fetch the full file record and return a normalised shape
 *    so the rest of the app always has: id, original_filename, size_bytes,
 *    pipeline_id, status, etc.
 */
export const uploadFile = async (formData) => {
  // Let axios handle multipart Content-Type + boundary automatically
  const response = await apiClient.post('/files/upload', formData);
  const { file_id, pipeline_id } = response.data;

  // /files/{id} returns { file: {...}, pipeline: {...}, artifacts: [...] }
  const detailResponse = await apiClient.get(`/files/${file_id}`);
  const fileRecord = detailResponse.data?.file || detailResponse.data;

  return {
    id:                file_id,
    pipeline_id:       pipeline_id,
    original_filename: fileRecord.original_filename,
    size_bytes:        fileRecord.size_bytes,
    file_size:         fileRecord.size_bytes,   // legacy alias
    page_count:        fileRecord.page_count || null,
    status:            fileRecord.status,
    file_type:         fileRecord.file_type,
    created_at:        fileRecord.created_at,
    storage_uri:       fileRecord.storage_uri,
  };
};

/**
 * Fetch all uploaded files.
 * Returns a flat array of file records.
 */
export const fetchUploadedFiles = async () => {
  const response = await apiClient.get('/files');
  return response.data;
};

/**
 * Fetch a single file record.
 * Endpoint returns { file: {...}, pipeline: {...}, artifacts: [...] }.
 * We unwrap and return the flat file object.
 */
export const fetchUploadedFileDetail = async (fileId) => {
  const response = await apiClient.get(`/files/${fileId}`);
  // Unwrap the envelope — the backend returns { file: {...}, ... }
  return response.data?.file || response.data;
};

export const fetchPdfContent = async (fileId) => {
  const response = await apiClient.get(`/api/v1/files/${fileId}/content`, {
    responseType: 'blob'
  });
  return response.data;
};
