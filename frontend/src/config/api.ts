// API Configuration
// This file centralizes API configuration to avoid hardcoded URLs

// Determine the API base URL based on environment
const getApiBaseUrl = (): string => {
  // Check if we're in development mode
  if (process.env.NODE_ENV === 'development') {
    // Use environment variable if set, otherwise default to localhost
    return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  }
  
  // Production API URL (you can set this via environment variable)
  return process.env.NEXT_PUBLIC_API_URL || 'https://rag-fill2-1.onrender.com';
};

export const API_CONFIG = {
  BASE_URL: getApiBaseUrl(),
  ENDPOINTS: {
    DEVICES: '/api/devices',
    DOCUMENTS: '/api/documents',
    CHAT: '/api/chat',
    TEMPLATES: '/api/templates',
  },
  TIMEOUT: 30000, // 30 seconds
} as const;

// Helper function to build API URLs
export const buildApiUrl = (endpoint: string): string => {
  return `${API_CONFIG.BASE_URL}${endpoint}`;
};

// Export for backward compatibility
export const API_BASE_URL = API_CONFIG.BASE_URL;
