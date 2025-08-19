// API Configuration
// This file centralizes API configuration to avoid hardcoded URLs

// Define a small type to avoid using `any` when accessing runtime globals
type RuntimeGlobals = {
  __NEXT_PUBLIC_BACKEND_BASE_URL?: string;
};

// Determine the API base URL based on environment and runtime overrides
const getApiBaseUrl = (): string => {
  // 1) Runtime override (set on globalThis if needed)
  const runtimeOverride = (globalThis as unknown as RuntimeGlobals).__NEXT_PUBLIC_BACKEND_BASE_URL;
  if (typeof runtimeOverride === 'string' && runtimeOverride.trim() !== '') {
    return runtimeOverride.replace(/\/$/, '');
  }

  // 2) Build-time env var (NEXT_PUBLIC_ is exposed to client builds)
  const envUrl = process.env.NEXT_PUBLIC_BACKEND_BASE_URL;
  if (envUrl && envUrl.trim() !== '') return envUrl.replace(/\/$/, '');

  // 3) If running in the browser, prefer current origin in production (useful when backend is same host or proxied)
  if (typeof window !== 'undefined') {
    if (process.env.NODE_ENV === 'development') {
      return 'http://localhost:8000';
    }
    return window.location.origin;
  }

  // 4) Server-side fallback
  if (process.env.NODE_ENV === 'development') {
    return 'http://localhost:8000';
  }
  return 'https://rag-fill2-1.onrender.com';
};

// Compute base once and also write it to globalThis so other runtime code can read/override it
const RUNTIME_API_BASE = getApiBaseUrl();
(globalThis as unknown as RuntimeGlobals).__NEXT_PUBLIC_BACKEND_BASE_URL = RUNTIME_API_BASE;

export const API_CONFIG = {
  BASE_URL: RUNTIME_API_BASE,
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

// Export device vectors URL from env if present (use exact env var name), else fall back to BASE_URL
export const DEVICE_VECTORS_URL =
  (process.env.NEXT_PUBLIC_DEVICE_VECTORS_URL && process.env.NEXT_PUBLIC_DEVICE_VECTORS_URL.replace(/\/$/, ''))
  || `${API_CONFIG.BASE_URL}/api/device-vectors`;
