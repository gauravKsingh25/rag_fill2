// API Configuration
// This file centralizes API configuration to avoid hardcoded URLs

// Define the runtime globals interface
interface RuntimeGlobals {
  __NEXT_PUBLIC_BACKEND_BASE_URL?: string;
}

// Determine the API base URL based on environment
const getApiBaseUrl = (): string => {
  // 1) Runtime override (set on globalThis if needed)
  const runtimeOverride = (globalThis as unknown as RuntimeGlobals).__NEXT_PUBLIC_BACKEND_BASE_URL;
  if (typeof runtimeOverride === 'string' && runtimeOverride.trim() !== '') {
    return runtimeOverride.replace(/\/$/, '');
  }

  // 2) Build-time env var (NEXT_PUBLIC_ is exposed to client builds)
  const envUrl = process.env.NEXT_PUBLIC_BACKEND_BASE_URL;
  if (envUrl && envUrl.trim() !== '') return envUrl.replace(/\/$/, '');

  // 3) Fallback to development URL if no environment variable is set
  // Check if we're in development mode
  if (process.env.NODE_ENV === 'development') {
    // Use environment variable if set, otherwise default to localhost
    return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  }

  // 4) Production fallback
  // Use production API URL if available, otherwise throw an error
  const productionUrl = process.env.NEXT_PUBLIC_API_URL || 'https://rag-fill2-1.onrender.com';
  if (productionUrl) {
    return productionUrl;
  }

  // If no URL is available, throw an error
  throw new Error('NEXT_PUBLIC_BACKEND_BASE_URL environment variable is required in production');
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
