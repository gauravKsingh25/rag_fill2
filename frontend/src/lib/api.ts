// API configuration and utilities

// Type definitions
export interface Device {
  id: string;
  name: string;
  description: string;
  namespace: string;
  allowed_file_types: string[];
  max_documents: number;
  embedding_model: string;
  created_at: string;
  is_active: boolean;
}

export interface DocumentMetadata {
  document_id: string;
  filename: string;
  file_size: number;
  file_type: string;
  upload_timestamp: string;
  device_id: string;
  chunk_count: number;
  processed: boolean;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface ChatResponse {
  response: string;
  sources: Array<{
    filename: string;
    chunk_id: number;
    score: number;
    content_preview: string;
  }>;
  device_id: string;
}

export interface TemplateAnalysis {
  device_id: string;
  template_filename: string;
  total_fields: number;
  fillable_fields: number;
  field_analysis: Record<string, {
    can_fill: boolean;
    confidence: number;
    sources: number;
  }>;
}

export interface UploadResponse {
  document_id?: string;
  filename: string;
  device_id: string;
  status: string;
  message: string;
  filled_template_url?: string;
  filled_fields?: Record<string, string>;
  missing_fields?: string[];
}

const API_BASE_URL = 'https://rag-fill2-1.onrender.com';

export const apiEndpoints = {
  devices: {
    list: () => `${API_BASE_URL}/api/devices/`,
    get: (deviceId: string) => `${API_BASE_URL}/api/devices/${deviceId}`,
    stats: (deviceId: string) => `${API_BASE_URL}/api/devices/${deviceId}/stats`,
    activate: (deviceId: string) => `${API_BASE_URL}/api/devices/${deviceId}/activate`,
    deactivate: (deviceId: string) => `${API_BASE_URL}/api/devices/${deviceId}/deactivate`,
  },
  documents: {
    upload: () => `${API_BASE_URL}/api/documents/upload`,
    listByDevice: (deviceId: string) => `${API_BASE_URL}/api/documents/device/${deviceId}`,
    get: (documentId: string) => `${API_BASE_URL}/api/documents/${documentId}`,
    delete: (documentId: string) => `${API_BASE_URL}/api/documents/${documentId}`,
    reprocess: (documentId: string) => `${API_BASE_URL}/api/documents/${documentId}/reprocess`,
  },
  chat: {
    send: () => `${API_BASE_URL}/api/chat/`,
    history: (sessionId: string) => `${API_BASE_URL}/api/chat/history/${sessionId}`,
    search: () => `${API_BASE_URL}/api/chat/search`,
  },
  templates: {
    analyze: () => `${API_BASE_URL}/api/templates/analyze`,
    uploadAndFill: () => `${API_BASE_URL}/api/templates/upload-and-fill`,
    download: (filename: string) => `${API_BASE_URL}/api/templates/download/${filename}`,
  },
} as const;

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public response?: Response | Record<string, unknown>
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export const apiRequest = async <T = unknown>(
  url: string,
  options: RequestInit = {}
): Promise<T> => {
  try {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorMessage;
      } catch {
        // If JSON parsing fails, use the default error message
      }
      throw new ApiError(errorMessage, response.status, response);
    }

    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return await response.json();
    }
    
    return response as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(
      error instanceof Error ? error.message : 'Network error',
      0
    );
  }
};

export const uploadFile = async <T = UploadResponse>(
  url: string,
  file: File,
  additionalData: Record<string, string> = {},
  onProgress?: (progress: number) => void
): Promise<T> => {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append('file', file);
    
    Object.entries(additionalData).forEach(([key, value]) => {
      formData.append(key, value);
    });

    const xhr = new XMLHttpRequest();

    if (onProgress) {
      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable) {
          const progress = (event.loaded / event.total) * 100;
          onProgress(progress);
        }
      });
    }

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const response = JSON.parse(xhr.responseText);
          resolve(response);
        } catch {
          resolve(xhr.responseText as T);
        }
      } else {
        try {
          const errorData = JSON.parse(xhr.responseText);
          reject(new ApiError(
            errorData.detail || `HTTP ${xhr.status}: ${xhr.statusText}`,
            xhr.status,
            errorData
          ));
        } catch {
          reject(new ApiError(
            `HTTP ${xhr.status}: ${xhr.statusText}`,
            xhr.status
          ));
        }
      }
    });

    xhr.addEventListener('error', () => {
      reject(new ApiError('Network error', 0));
    });

    xhr.open('POST', url);
    xhr.send(formData);
  });
};

// Utility functions for common API operations
export const deviceApi = {
  list: () => apiRequest<Device[]>(apiEndpoints.devices.list()),
  get: (deviceId: string) => apiRequest<Device>(apiEndpoints.devices.get(deviceId)),
  getStats: (deviceId: string) => apiRequest<Record<string, unknown>>(apiEndpoints.devices.stats(deviceId)),
};

export const documentApi = {
  upload: (file: File, deviceId: string, onProgress?: (progress: number) => void) =>
    uploadFile<UploadResponse>(apiEndpoints.documents.upload(), file, { device_id: deviceId }, onProgress),
  listByDevice: (deviceId: string) => apiRequest<{ documents: DocumentMetadata[]; device_id: string; document_count: number }>(apiEndpoints.documents.listByDevice(deviceId)),
  delete: (documentId: string) => apiRequest<{ message: string; document_id: string; device_id: string }>(apiEndpoints.documents.delete(documentId), { method: 'DELETE' }),
};

export const chatApi = {
  send: (deviceId: string, message: string, conversationHistory: ChatMessage[] = []) =>
    apiRequest<ChatResponse>(apiEndpoints.chat.send(), {
      method: 'POST',
      body: JSON.stringify({
        device_id: deviceId,
        message,
        conversation_history: conversationHistory,
      }),
    }),
  search: (deviceId: string, query: string, topK: number = 5) =>
    apiRequest<{
      device_id: string;
      query: string;
      results_count: number;
      results: Array<{
        content: string;
        filename: string;
        chunk_id: number;
        score: number;
        document_id: string;
      }>;
    }>(apiEndpoints.chat.search(), {
      method: 'POST',
      body: JSON.stringify({
        device_id: deviceId,
        query,
        top_k: topK,
      }),
    }),
};

export const templateApi = {
  analyze: (file: File, deviceId: string) =>
    uploadFile<TemplateAnalysis>(apiEndpoints.templates.analyze(), file, { device_id: deviceId }),
  uploadAndFill: (file: File, deviceId: string) =>
    uploadFile<UploadResponse>(apiEndpoints.templates.uploadAndFill(), file, { device_id: deviceId }),
};
